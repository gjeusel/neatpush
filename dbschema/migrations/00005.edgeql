CREATE MIGRATION m13p7bt6qbuodaiutmsxyst34wbd6swmiwokou5lu4nxy6hwxnnlxq
    ONTO m1pjzrmvxytckazqfaaidkbhsfmzmo74smsor7cirx36rqfigm5vuq
{
  ALTER TYPE default::MangaChapter {
      CREATE PROPERTY notified := (.notif_status.notified);
  };
};
