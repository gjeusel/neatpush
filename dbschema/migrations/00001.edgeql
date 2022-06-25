CREATE MIGRATION m1fwpognwu55gd64ljzvkqpho6x53phrhlpfxwdk5v6tfpovghpfwa
    ONTO initial
{
  CREATE TYPE default::MangaChapter {
      CREATE REQUIRED PROPERTY name -> std::str;
      CREATE PROPERTY timestamp -> std::datetime {
          SET default := (std::datetime_current());
      };
      CREATE PROPERTY url -> std::str;
  };
  CREATE TYPE default::Manga {
      CREATE MULTI LINK chapters -> default::MangaChapter;
      CREATE REQUIRED PROPERTY name -> std::str;
  };
};
