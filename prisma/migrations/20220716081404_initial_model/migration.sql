-- CreateTable
CREATE TABLE "MangaChapter" (
    "id" TEXT NOT NULL PRIMARY KEY,
    "num" TEXT NOT NULL,
    "timestamp" DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP,
    "url" TEXT NOT NULL,
    "notified" BOOLEAN NOT NULL DEFAULT false,
    "mangaId" TEXT NOT NULL,
    CONSTRAINT "MangaChapter_mangaId_fkey" FOREIGN KEY ("mangaId") REFERENCES "Manga" ("id") ON DELETE RESTRICT ON UPDATE CASCADE
);

-- CreateTable
CREATE TABLE "Manga" (
    "id" TEXT NOT NULL PRIMARY KEY,
    "name" TEXT NOT NULL
);

-- CreateIndex
CREATE UNIQUE INDEX "MangaChapter_mangaId_key" ON "MangaChapter"("mangaId");

-- CreateIndex
CREATE UNIQUE INDEX "Manga_name_key" ON "Manga"("name");
