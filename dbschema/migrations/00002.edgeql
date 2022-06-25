CREATE MIGRATION m1ysxezgz4cfewhxupzcgqspanddgbokfzkx33lz7rwdz3e32q6fjq
    ONTO m1fwpognwu55gd64ljzvkqpho6x53phrhlpfxwdk5v6tfpovghpfwa
{
  CREATE TYPE default::NotifStatus {
      CREATE REQUIRED PROPERTY notified -> std::bool {
          SET default := false;
      };
      CREATE PROPERTY timestamp -> std::datetime;
  };
  ALTER TYPE default::MangaChapter {
      CREATE REQUIRED LINK notif_status -> default::NotifStatus {
          SET default := (std::assert_single((INSERT
              default::NotifStatus
              {
                  notified := false
              })));
      };
  };
};
