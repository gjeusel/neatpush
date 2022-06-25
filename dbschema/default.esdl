module default {

  type NotifStatus {
    required property notified -> bool { default := false };
    property timestamp -> datetime;
  }

  type MangaChapter {
    required property num -> str;

    property timestamp -> datetime { default := std::datetime_current() };
    property url -> str { constraint exclusive };

    required link manga -> Manga;
    required link notif_status -> NotifStatus {
      default := assert_single((insert NotifStatus {notified := false}))
    };
  }

  type Manga {
    required property name -> str {
      constraint exclusive;
    };
  }


}
