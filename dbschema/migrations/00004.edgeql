CREATE MIGRATION m1pjzrmvxytckazqfaaidkbhsfmzmo74smsor7cirx36rqfigm5vuq
    ONTO m1fkwehkzmqs36ph4u6yd4jiiqoakg6gatch6ev6xh4vzvrhkredkq
{
  ALTER TYPE default::Manga {
      DROP LINK chapters;
  };
  ALTER TYPE default::MangaChapter {
      CREATE REQUIRED LINK manga -> default::Manga {
          SET REQUIRED USING (std::assert_single((SELECT
              default::Manga
          FILTER
              (.name = 'berserk')
          )));
      };
  };
  ALTER TYPE default::MangaChapter {
      ALTER PROPERTY name {
          RENAME TO num;
      };
  };
};
