CREATE MIGRATION m1wbgutya7zzynk4c5itsomcka3bdeanp472xcan54kfaazb7y2faq
    ONTO m1rtwyi6buxrnaappj33uimwzm7jpoji5rx4scrucyzrjofn6tgphq
{
  ALTER TYPE default::Manga {
      CREATE MULTI LINK chapters := (.<manga[IS default::MangaChapter]);
  };
  ALTER TYPE default::NotifStatus {
      CREATE MULTI LINK chapters := (.<notif_status[IS default::MangaChapter]);
  };
};
