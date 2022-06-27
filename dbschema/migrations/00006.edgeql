CREATE MIGRATION m1rtwyi6buxrnaappj33uimwzm7jpoji5rx4scrucyzrjofn6tgphq
    ONTO m13p7bt6qbuodaiutmsxyst34wbd6swmiwokou5lu4nxy6hwxnnlxq
{
  ALTER TYPE default::MangaChapter {
      DROP PROPERTY notified;
  };
};
