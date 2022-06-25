CREATE MIGRATION m1fkwehkzmqs36ph4u6yd4jiiqoakg6gatch6ev6xh4vzvrhkredkq
    ONTO m1ysxezgz4cfewhxupzcgqspanddgbokfzkx33lz7rwdz3e32q6fjq
{
  ALTER TYPE default::Manga {
      ALTER PROPERTY name {
          CREATE CONSTRAINT std::exclusive;
      };
  };
  ALTER TYPE default::MangaChapter {
      ALTER PROPERTY url {
          CREATE CONSTRAINT std::exclusive;
      };
  };
};
