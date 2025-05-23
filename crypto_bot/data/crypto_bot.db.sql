BEGIN TRANSACTION;
CREATE TABLE IF NOT EXISTS "coin_data_cache" (
	"coin_id"	TEXT,
	"data"	TEXT NOT NULL,
	"last_updated"	REAL NOT NULL,
	PRIMARY KEY("coin_id")
);
CREATE TABLE IF NOT EXISTS "news_cache" (
	"query"	TEXT,
	"result"	TEXT NOT NULL,
	"date"	TEXT NOT NULL,
	PRIMARY KEY("query")
);
CREATE TABLE IF NOT EXISTS "price_averages_cache" (
	"coin_id"	TEXT,
	"data"	TEXT NOT NULL,
	"last_updated"	REAL NOT NULL,
	PRIMARY KEY("coin_id")
);
CREATE TABLE IF NOT EXISTS "project_sources_cache" (
	"coin_id"	TEXT,
	"data"	TEXT NOT NULL,
	"last_updated"	REAL NOT NULL,
	PRIMARY KEY("coin_id")
);
CREATE TABLE IF NOT EXISTS "projects_cache" (
	"coin_id"	TEXT,
	"data"	TEXT NOT NULL,
	"last_updated"	REAL NOT NULL,
	PRIMARY KEY("coin_id")
);
CREATE TABLE IF NOT EXISTS "thread_history" (
	"timestamp"	REAL,
	"post_hashes"	TEXT,
	"influencers"	TEXT,
	PRIMARY KEY("timestamp")
);
CREATE TABLE IF NOT EXISTS "youtube_cache" (
	"query"	TEXT,
	"result"	TEXT NOT NULL,
	"last_updated"	REAL NOT NULL,
	PRIMARY KEY("query")
);
CREATE TABLE IF NOT EXISTS "youtube_summary_cache" (
	"query"	TEXT,
	"result"	TEXT NOT NULL,
	"last_updated"	REAL NOT NULL,
	PRIMARY KEY("query")
);
INSERT INTO "projects_cache" VALUES ('ripple','[["Sologenic", "Tokenizes assets like stocks on XRPL", "https://sologenic.org"], ["XRPL Labs", "Building Xumm wallet for XRPL", "https://xrpl-labs.com"]]',1747006214.83643);
COMMIT;
