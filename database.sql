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

-- Keep track of how far we've processed the various logfiles/milestones.
CREATE TABLE logfile_offsets (
  filename VARCHAR(100) PRIMARY KEY,
  offset BIGINT DEFAULT 0
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
  
  -- Source logfile. This should be sufficient to identify the server
  -- involved.
  source_file VARCHAR(150),

  name VARCHAR(20),
  start_time DATETIME,
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
CREATE INDEX wins_name ON wins (name);

CREATE TABLE all_recent_games AS SELECT * FROM player_best_games;
ALTER TABLE all_recent_games ADD CONSTRAINT PRIMARY KEY (id);
ALTER TABLE all_recent_games CHANGE COLUMN id id BIGINT AUTO_INCREMENT;
CREATE INDEX all_recent_games_end
ON all_recent_games (end_time DESC);

CREATE TABLE player_recent_games AS SELECT * FROM player_best_games;
ALTER TABLE player_recent_games ADD CONSTRAINT PRIMARY KEY (id);
ALTER TABLE player_recent_games CHANGE COLUMN id id BIGINT AUTO_INCREMENT;
CREATE INDEX player_recent_games_name_end
ON player_recent_games (name, end_time DESC);

-- Table for the top games on the servers. How many games we keep here
-- is controlled by the Python code.
-- We want all the same field names, etc. for all games tables, so we create
-- each new table based on the canonical game table (player_best_games).
CREATE TABLE top_games AS SELECT * FROM player_best_games;
ALTER TABLE top_games ADD CONSTRAINT PRIMARY KEY (id);
ALTER TABLE top_games CHANGE COLUMN id id BIGINT AUTO_INCREMENT;
CREATE INDEX top_games_sc ON top_games (sc);

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
CREATE INDEX streak_games_name_time ON streak_games (name, end_time);

CREATE TABLE streak_breakers AS SELECT * FROM player_best_games;
ALTER TABLE streak_breakers ADD CONSTRAINT PRIMARY KEY (id);
ALTER TABLE streak_breakers CHANGE COLUMN id id BIGINT AUTO_INCREMENT;
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

  -- Combo they're currently playing; used in the active streaks
  -- table. This will be set to NULL on end of game, and will only be
  -- set to a new value if currently NULL.
  current_combo CHAR(4)
  );
CREATE INDEX player_total_scores ON players (name, total_score);

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
  ckiller VARCHAR(100),
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