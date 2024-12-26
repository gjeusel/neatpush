from __future__ import annotations

import hashlib
import hmac
import mimetypes
import re
from binascii import hexlify
from collections.abc import Generator
from datetime import UTC, datetime
from functools import reduce
from pathlib import Path
from typing import Annotated, Any, ClassVar, Literal, overload
from urllib.parse import quote as url_quote

import httpx
import tenacity
from pydantic import (
    AliasGenerator,
    BaseModel,
    BeforeValidator,
    ConfigDict,
    Field,
    SecretStr,
)
from pydantic.alias_generators import to_pascal

type HttpMethodT = Literal["GET", "POST", "PUT", "DELETE"] | str

xmlns = "http://s3.amazonaws.com/doc/2006-03-01/"
xmlns_pattern = re.compile(f' xmlns="{re.escape(xmlns)}"'.encode())

_AWS_AUTH_REQUEST = "aws4_request"
_CONTENT_TYPE = "application/x-www-form-urlencoded"
_AUTH_ALGORITHM = "AWS4-HMAC-SHA256"

_METADATA_HEADER_PREFIX = "x-amz-meta-"
_ACL_HEADER = "x-amz-acl"


def _aws4_date_stamp(dt: datetime) -> str:
    return dt.strftime("%Y%m%d")


def _aws4_x_amz_date(dt: datetime) -> str:
    return dt.strftime("%Y%m%dT%H%M%SZ")


def _aws4_reduce_signature(key: bytes, msg: str) -> bytes:
    return hmac.new(key, msg.encode(), hashlib.sha256).digest()


@overload
def _sanitize_path(value: None) -> None: ...
@overload
def _sanitize_path(value: str | Path) -> str: ...
def _sanitize_path(value: str | Path | None) -> str | None:
    if value is None:
        return value

    if isinstance(value, Path):
        value = value.as_posix()

    if value.startswith("/"):
        return value.lstrip("/")

    return value


class S3ClientError(Exception):
    pass


class S3FileDoesNotExist(S3ClientError):
    def __init__(self, file: str) -> None:
        self.file = file
        super().__init__(f"'{file}' does not exists.")


class S3RequestError(S3ClientError):
    def __init__(self, r: httpx.Response) -> None:
        error_msg = f'unexpected response from {r.request.method} "{r.request.url}": {r.status_code}'
        super().__init__(error_msg)
        self.response = r
        self.status = r.status_code

    def __str__(self) -> str:
        if self.response.headers.get("content-type") == "application/xml":
            text = pretty_xml(self.response.content)
        else:
            text = self.response.text
        return f"{self.args[0]}, response:\n{text}"


def pretty_xml(response_xml: bytes) -> str:
    import xml.dom.minidom

    try:
        pretty = xml.dom.minidom.parseString(response_xml).toprettyxml(indent="  ")  # noqa: S318
    except Exception:  # pragma: no cover
        return response_xml.decode()
    else:
        return f"{pretty} (XML formatted)"


class S3File(BaseModel):
    key: str
    last_modified: datetime
    size: int
    e_tag: Annotated[str, BeforeValidator(lambda x: x.strip('"'))]
    storage_class: str

    metadata: dict[str, str] = Field(default_factory=dict)

    model_config = ConfigDict(
        alias_generator=AliasGenerator(
            validation_alias=to_pascal,
        ),
        populate_by_name=True,
    )


class AWSv4Auth(BaseModel, httpx.Auth):
    access_key: str
    secret_key: SecretStr
    region: str

    service: ClassVar[str] = "s3"

    def auth_headers(
        self,
        method: HttpMethodT,
        url: httpx.URL,
        *,
        data: bytes | None = None,
        content_type: str | None = None,
    ) -> dict[str, str]:
        now = datetime.now(tz=UTC)
        data = data or b""
        content_type = content_type or _CONTENT_TYPE

        payload_hash = hashlib.sha256(data).hexdigest()

        # WARNING! order is important here, headers need to be in alphabetical order
        headers = {
            "host": url.host,
            "x-amz-date": _aws4_x_amz_date(now),
            "x-amz-content-sha256": payload_hash,
        }

        signed_headers, signature = self.aws4_signature(
            now, method, url, headers, payload_hash
        )
        credential = self.aws4_credential(now)
        authorization_header = (
            f"{_AUTH_ALGORITHM} Credential={credential},"
            f" SignedHeaders={signed_headers}, Signature={signature}"
        )
        headers |= {
            "authorization": authorization_header,
            "content-length": str(len(data)),
            "content-type": content_type,
        }

        return headers

    def aws4_signature(
        self,
        dt: datetime,
        method: HttpMethodT,
        url: httpx.URL,
        headers: dict[str, Any],
        payload_hash: str,
    ) -> tuple[str, str]:
        header_keys = sorted(headers)
        signed_headers = ";".join(header_keys)
        canonical_request_parts = (
            method,
            url_quote(url.path),
            url.query.decode(),
            "".join(f"{k}:{headers[k]}\n" for k in header_keys),
            signed_headers,
            payload_hash,
        )
        canonical_request = "\n".join(canonical_request_parts)
        string_to_sign_parts = (
            _AUTH_ALGORITHM,
            _aws4_x_amz_date(dt),
            self._aws4_scope(dt),
            hashlib.sha256(canonical_request.encode()).hexdigest(),
        )
        string_to_sign = "\n".join(string_to_sign_parts)
        return signed_headers, self.aws4_sign_string(string_to_sign, dt)

    def aws4_sign_string(self, string_to_sign: str, dt: datetime) -> str:
        key_parts = (
            ("AWS4" + self.secret_key.get_secret_value()).encode(),
            _aws4_date_stamp(dt),
            self.region,
            self.service,
            _AWS_AUTH_REQUEST,
            string_to_sign,
        )
        signature_bytes: bytes = reduce(_aws4_reduce_signature, key_parts)  # type: ignore
        return hexlify(signature_bytes).decode()

    def _aws4_scope(self, dt: datetime) -> str:
        return (
            f"{_aws4_date_stamp(dt)}/{self.region}/{self.service}/{_AWS_AUTH_REQUEST}"
        )

    def aws4_credential(self, dt: datetime) -> str:
        return f"{self.access_key}/{self._aws4_scope(dt)}"

    # --

    def auth_flow(
        self, request: httpx.Request
    ) -> Generator[httpx.Request, httpx.Response]:
        # WARNING! url query params order is important here, need to be in alphabetical order
        url = httpx.URL(
            f"https://{request.url.host}{request.url.path}",
            params=sorted(request.url.params.items()),
        )

        headers = self.auth_headers(
            method=request.method,
            url=url,
            data=request.read(),
            content_type=request.headers.get("content-type"),
        )
        request.headers.update(headers)
        yield request


class S3Client:
    def __init__(
        self,
        access_key: str,
        secret_key: str | SecretStr,
        bucket: str,
        base_url: str,
        region: str,
        client: httpx.Client | None = None,
    ) -> None:
        self.bucket = bucket

        auth = AWSv4Auth(
            access_key=access_key,
            secret_key=secret_key,
            region=region,
        )

        self.http = client or httpx.Client(
            base_url=base_url,
            auth=auth,
            timeout=httpx.Timeout(timeout=10, connect=3),
            limits=httpx.Limits(max_connections=64),
            transport=httpx.HTTPTransport(retries=5),
        )

        # add retries capabilities:
        self.http.request = tenacity.retry(  # type: ignore[method-assign]
            stop=tenacity.stop_after_attempt(5),
            retry=tenacity.retry_if_exception(
                lambda x: isinstance(x, S3RequestError) and x.status == 500
            ),
        )(self.http.request)

        self.http.request = tenacity.retry(  # type: ignore[method-assign]
            stop=tenacity.stop_after_attempt(5),
            retry=tenacity.retry_if_exception(
                lambda x: isinstance(x, httpx.RemoteProtocolError)
                and "Server disconnected without sending a response." == str(x)
            ),
        )(self.http.request)

    def upload(
        self,
        filepath: str | Path,
        content: bytes,
        *,
        content_type: str | None = None,
        metadata: dict[str, Any] | None = None,
        is_public: bool | None = False,
    ) -> None:
        filepath = _sanitize_path(filepath)
        content_type = (
            content_type
            or mimetypes.guess_type(filepath)[0]
            or "application/octet-stream"
        )

        endpoint = f"{self.bucket}/{url_quote(filepath)}"

        headers = {
            "content-type": content_type,
            "content-length": str(len(content)),
        }
        if metadata:
            for key, value in metadata.items():
                headers[f"{_METADATA_HEADER_PREFIX}{key}"] = str(value)

        if is_public:
            headers[_ACL_HEADER] = "public-read"

        r = self.http.put(
            endpoint,
            content=content,
            headers=headers,
        )

        if r.status_code == 200:
            return None
        else:
            raise S3RequestError(r)

    def download(self, filepath: str | Path) -> bytes:
        filepath = _sanitize_path(filepath)
        endpoint = f"{self.bucket}/{url_quote(filepath)}"

        resp = self.http.get(endpoint)
        if resp.status_code == 404:
            raise S3FileDoesNotExist(filepath)

        resp.raise_for_status()

        return resp.content
