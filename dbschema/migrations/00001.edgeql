CREATE MIGRATION m1q5tfkk5ncerit4x5ouv2qgarzkd4ewbttfrkjfrilkp76273kjwa
    ONTO initial
{
  CREATE TYPE default::Manga {
      CREATE REQUIRED PROPERTY name -> std::str {
          CREATE CONSTRAINT std::exclusive;
      };
  };
  CREATE TYPE default::MangaChapter {
      CREATE REQUIRED LINK manga -> default::Manga;
      CREATE PROPERTY notified -> std::bool {
          SET default := false;
      };
      CREATE REQUIRED PROPERTY num -> std::str;
      CREATE PROPERTY timestamp -> std::datetime {
          SET default := (std::datetime_current());
      };
      CREATE PROPERTY url -> std::str {
          CREATE CONSTRAINT std::exclusive;
      };
  };
  ALTER TYPE default::Manga {
      CREATE MULTI LINK chapters := (.<manga[IS default::MangaChapter]);
  };
};
