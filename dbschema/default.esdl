module default {
  type MangaChapter {
    required property num -> str;

    property timestamp -> datetime { default := std::datetime_current() };
    property url -> str { constraint exclusive };

    required link manga -> Manga;

    property notified -> bool { default := false };

  }

  type Manga {
    required property name -> str {
      constraint exclusive;
    };

    multi link chapters := .<manga[is MangaChapter]
  }
}
