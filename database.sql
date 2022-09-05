-- Use InnoDB for transaction support?
-- SET storage_engine=InnoDB;

DROP TABLE IF EXISTS logfile_offsets;
DROP TABLE IF EXISTS player_recent_games;
DROP TABLE IF EXISTS all_recent_games;
DROP TABLE IF EXISTS player_best_games;
DROP TABLE IF EXISTS player_last_games;
DROP TABLE IF EXISTS player_first_games;
DROP TABLE IF EXISTS streak_games;
DROP TABLE IF EXISTS streak_breakers;
DROP TABLE IF EXISTS wins;
DROP TABLE IF EXISTS streaks;
DROP TABLE IF EXISTS top_games;
DROP TABLE IF EXISTS top_combo_scores;
DROP TABLE IF EXISTS top_species_scores;
DROP TABLE IF EXISTS top_class_scores;
DROP TABLE IF EXISTS players;
DROP TABLE IF EXISTS player_char_stats;
DROP TABLE IF EXISTS top_killers;
DROP TABLE IF EXISTS killer_recent_kills;
DROP TABLE IF EXISTS ghost_victims;
DROP TABLE IF EXISTS low_xl_rune_finds;
DROP TABLE IF EXISTS ziggurats;
DROP TABLE IF EXISTS per_day_stats;
DROP TABLE IF EXISTS date_players;
DROP TABLE IF EXISTS known_races;
DROP TABLE IF EXISTS known_classes;
DROP TABLE IF EXISTS botnames;
DROP TABLE IF EXISTS version_triage;

-- Keep track of how far we've processed the various logfiles/milestones.
CREATE TABLE logfile_offsets (
  id INT AUTO_INCREMENT PRIMARY KEY,
  filename VARCHAR(100) UNIQUE,
  offset BIGINT DEFAULT 0
);

CREATE TABLE botnames (
  name VARCHAR(20) UNIQUE NOT NULL
);

-- [greensnark] I've changed the field names for tables containing
-- game entries to be closer to the logfile names. This is
-- inconsistent with the tourney db and with Henzell's primary db,
-- which sucks, but reducing the number of differences between logfile
-- names and field names seems quite important to me.

-- Best games on a per-player basis. Adding a new game must also delete the
-- previous entry by that player.
CREATE TABLE player_best_games (
  id BIGINT AUTO_INCREMENT PRIMARY KEY,
  
  -- Source logfile.
  source_file VARCHAR(150),

  -- game_key in Sequell format. This is reconstructable from other things in
  -- the table, as long as you know the logfile->server mappings, but it is
  -- convenient to have as its own field.
  game_key VARCHAR(50) NOT NULL,

  name VARCHAR(20),
  start_time DATETIME,
  seed VARCHAR(255), -- currently 64bit uint, but allow extra space for changes
  sc BIGINT,
  race VARCHAR(20),
  crace VARCHAR(20),
  -- Two letter race abbreviation so we can group by it without pain.
  raceabbr CHAR(2) NOT NULL,
  clsabbr CHAR(2) NOT NULL,
  cls VARCHAR(20),
  v VARCHAR(10),
  lv VARCHAR(8),
  uid INT,
  charabbr CHAR(4),
  xl INT,
  sk VARCHAR(16),
  sklev INT,
  title VARCHAR(255),
  place VARCHAR(16),
  br VARCHAR(16),
  lvl INT,
  ltyp VARCHAR(16),
  hp INT,
  mhp INT,
  mmhp INT,
  strength INT,
  intelligence INT,
  dexterity INT,
  god VARCHAR(20),
  dur INT,
  turn BIGINT,
  ktyp VARCHAR(20),
  killer VARCHAR(100),
  kgroup VARCHAR(100),
  ckiller VARCHAR(100),
  kaux VARCHAR(255),
  -- Kills may be null.
  kills INT,
  dam INT,
  piety INT,
  pen INT,
  gold INT,
  goldfound INT,
  goldspent INT,
  end_time DATETIME,
  tmsg VARCHAR(255),
  vmsg VARCHAR(255),
  nrune INT DEFAULT 0,
  urune INT DEFAULT 0
);
CREATE INDEX player_best_game_pscores ON player_best_games (name, sc);

CREATE TABLE wins AS SELECT * FROM player_best_games;
ALTER TABLE wins ADD CONSTRAINT PRIMARY KEY (id);
ALTER TABLE wins CHANGE COLUMN id id BIGINT AUTO_INCREMENT;
CREATE UNIQUE INDEX wins_gid ON wins (game_key);
CREATE INDEX wins_name ON wins (name);
CREATE INDEX wins_dur ON wins (dur);
CREATE INDEX wins_turn ON wins (turn);
CREATE INDEX wins_sc ON wins (sc);

CREATE TABLE all_recent_games AS SELECT * FROM player_best_games;
ALTER TABLE all_recent_games ADD CONSTRAINT PRIMARY KEY (id);
ALTER TABLE all_recent_games CHANGE COLUMN id id BIGINT AUTO_INCREMENT;
CREATE INDEX all_recent_games_end
ON all_recent_games (end_time DESC);

CREATE TABLE player_recent_games AS SELECT * FROM player_best_games;
ALTER TABLE player_recent_games ADD CONSTRAINT PRIMARY KEY (id);
ALTER TABLE player_recent_games CHANGE COLUMN id id BIGINT AUTO_INCREMENT;
CREATE UNIQUE INDEX player_recent_gid ON player_recent_games (game_key);
CREATE INDEX player_recent_games_name_end
ON player_recent_games (name, end_time DESC);
CREATE INDEX player_recent_games_name_id
ON player_recent_games (name, id);

-- Table for the top games on the servers. How many games we keep here
-- is controlled by the Python code.
-- We want all the same field names, etc. for all games tables, so we create
-- each new table based on the canonical game table (player_best_games).
CREATE TABLE top_games AS SELECT * FROM player_best_games;
ALTER TABLE top_games ADD CONSTRAINT PRIMARY KEY (id);
ALTER TABLE top_games CHANGE COLUMN id id BIGINT AUTO_INCREMENT;
CREATE INDEX top_games_sc ON top_games (sc);

-- n.b. the unique class/job values will prevent duplicate games in these tables
-- Keep track of best score for each combo (unique charabbr).
CREATE TABLE top_combo_scores AS SELECT * FROM player_best_games;
ALTER TABLE top_combo_scores ADD CONSTRAINT PRIMARY KEY (id);
ALTER TABLE top_combo_scores CHANGE COLUMN id id BIGINT AUTO_INCREMENT;
ALTER TABLE top_combo_scores Add CONSTRAINT UNIQUE (charabbr);
CREATE INDEX top_combo_scores_name ON top_combo_scores (name, charabbr);
CREATE UNIQUE INDEX top_combo_scores_charabbr
ON top_combo_scores (charabbr);
CREATE INDEX top_combo_scores_sc ON top_combo_scores (sc);

-- Keep track of best score for each species (unique raceabbr).
CREATE TABLE top_species_scores AS SELECT * FROM player_best_games;
ALTER TABLE top_species_scores ADD CONSTRAINT PRIMARY KEY (id);
ALTER TABLE top_species_scores CHANGE COLUMN id id BIGINT AUTO_INCREMENT;
ALTER TABLE top_species_scores Add CONSTRAINT UNIQUE (raceabbr);
CREATE UNIQUE INDEX top_species_scores_raceabbr
ON top_species_scores (raceabbr);
CREATE INDEX top_species_scores_name ON top_species_scores (name, crace);

-- Keep track of best score for each species (unique cls).
CREATE TABLE top_class_scores AS SELECT * FROM player_best_games;
ALTER TABLE top_class_scores ADD CONSTRAINT PRIMARY KEY (id);
ALTER TABLE top_class_scores CHANGE COLUMN id id BIGINT AUTO_INCREMENT;
ALTER TABLE top_class_scores Add CONSTRAINT UNIQUE (cls);
CREATE UNIQUE INDEX top_class_scores_cls
ON top_class_scores (cls);
CREATE INDEX top_class_scores_name ON top_class_scores (name, cls);

-- Most recent game by every known player.
CREATE TABLE player_last_games AS SELECT * FROM player_best_games;
ALTER TABLE player_last_games ADD CONSTRAINT PRIMARY KEY (id);
ALTER TABLE player_last_games CHANGE COLUMN id id BIGINT AUTO_INCREMENT;
ALTER TABLE player_last_games Add CONSTRAINT UNIQUE (name);
CREATE UNIQUE INDEX player_last_games_name
ON player_last_games (name);

-- First known game by every known player
CREATE TABLE player_first_games AS SELECT * FROM player_best_games;
ALTER TABLE player_first_games ADD CONSTRAINT PRIMARY KEY (id);
ALTER TABLE player_first_games CHANGE COLUMN id id BIGINT AUTO_INCREMENT;
ALTER TABLE player_first_games Add CONSTRAINT UNIQUE (name);
CREATE UNIQUE INDEX player_first_games_name
ON player_first_games (name);

-- Streak games by all players; includes first game in the streak.
CREATE TABLE streak_games AS SELECT * FROM player_best_games;
ALTER TABLE streak_games ADD CONSTRAINT PRIMARY KEY (id);
ALTER TABLE streak_games CHANGE COLUMN id id BIGINT AUTO_INCREMENT;
ALTER TABLE streak_games ADD CONSTRAINT UNIQUE (game_key);
CREATE INDEX streak_games_name_time ON streak_games (name, end_time);

CREATE TABLE streak_breakers AS SELECT * FROM player_best_games;
ALTER TABLE streak_breakers ADD CONSTRAINT PRIMARY KEY (id);
ALTER TABLE streak_breakers CHANGE COLUMN id id BIGINT AUTO_INCREMENT;
ALTER TABLE streak_breakers ADD CONSTRAINT UNIQUE (game_key); -- is this needed;
ALTER TABLE streak_breakers ADD COLUMN streak_id BIGINT UNIQUE NOT NULL;

-- Track all streaks by all players.
CREATE TABLE streaks (
  id BIGINT AUTO_INCREMENT PRIMARY KEY,
  player VARCHAR(20),
  start_game_time DATETIME,
  end_game_time DATETIME,
  active BOOLEAN DEFAULT 0,
  ngames INT DEFAULT 0
);
CREATE INDEX streaks_order ON streaks (ngames DESC, id);
CREATE INDEX streaks_player ON streaks (player);
CREATE INDEX streaks_player_active ON streaks (player, active);

-- Player statistics
CREATE TABLE players (
  name VARCHAR(20) UNIQUE PRIMARY KEY,
  games_played INT DEFAULT 0,
  games_won INT DEFAULT 0,
  total_score BIGINT,
  best_xl TINYINT,
  best_score BIGINT,
  first_game_start DATETIME,
  last_game_end DATETIME,
  max_runes TINYINT DEFAULT 0,

  -- Combo they're currently playing; used in the active streaks
  -- table. This will be set to NULL on end of game, and will only be
  -- set to a new value if currently NULL.
  current_combo CHAR(4)
  );
CREATE INDEX player_total_scores ON players (name, total_score);
CREATE INDEX players_win_stats ON players (games_won DESC, games_played);

-- Statistics on the games the player has played.
CREATE TABLE player_char_stats (
  name VARCHAR(20),
  charabbr CHAR(4),
  games_played INT DEFAULT 0,
  best_xl INT DEFAULT 0,
  wins INT DEFAULT 0
);
CREATE UNIQUE INDEX player_cstats_name_char
                 ON player_char_stats (name, charabbr);
CREATE INDEX player_char_stats_name_cab ON player_char_stats (name, charabbr);

CREATE TABLE top_killers (
  ckiller VARCHAR(100) UNIQUE PRIMARY KEY,
  kills BIGINT DEFAULT 0,
  most_recent_victim VARCHAR(20)
);
CREATE INDEX top_killers_kills ON top_killers (kills DESC, ckiller);

CREATE TABLE killer_recent_kills AS SELECT * FROM player_best_games;
ALTER TABLE killer_recent_kills ADD CONSTRAINT PRIMARY KEY (id);
ALTER TABLE killer_recent_kills CHANGE COLUMN id id BIGINT AUTO_INCREMENT;
ALTER TABLE killer_recent_kills Add CONSTRAINT UNIQUE (ckiller);
CREATE INDEX killer_recent_kills_ckiller ON killer_recent_kills (ckiller);

CREATE TABLE ghost_victims (
  ghost VARCHAR(100),
  victim VARCHAR(20)
);
CREATE INDEX ghost_victims_ghost ON ghost_victims (ghost);
CREATE INDEX ghost_victims_victim ON ghost_victims (victim);

CREATE TABLE low_xl_rune_finds (
  player VARCHAR(20),
  start_time DATETIME,
  rune_time DATETIME,
  rune VARCHAR(50),
  xl TINYINT
);
CREATE INDEX rune_finds_xl ON low_xl_rune_finds (xl, rune_time);

-- Ziggurat visits; newer visits will overwrite older ones, unlike
-- most other tables.
CREATE TABLE ziggurats (
  id BIGINT AUTO_INCREMENT PRIMARY KEY,
  player VARCHAR(20),
  deepest INT,
  place VARCHAR(20),
  zig_time DATETIME,
  start_time DATETIME
);
CREATE INDEX ziggurats_time ON ziggurats (zig_time);

CREATE TABLE per_day_stats (
  which_day DATETIME UNIQUE PRIMARY KEY,
  games_ended INT DEFAULT 0,
  games_won INT DEFAULT 0
);

CREATE TABLE date_players (
  which_day DATETIME,
  which_month CHAR(6),
  player VARCHAR(20),
  games INT DEFAULT 0,
  wins INT DEFAULT 0,
  PRIMARY KEY (which_day, player)
);
CREATE INDEX date_players_month ON date_players (which_month);

CREATE TABLE known_races (
  race CHAR(2) UNIQUE PRIMARY KEY
);

CREATE TABLE known_classes (
  cls CHAR(2) UNIQUE PRIMARY KEY
);

CREATE TABLE version_triage(v VARCHAR(10) UNIQUE NOT NULL, major INT, stable BOOLEAN DEFAULT 0, vclean VARCHAR(10), recent BOOLEAN DEFAULT 0);
CREATE INDEX prg_v ON player_recent_games (v);
CREATE INDEX wins_v ON wins (v);
