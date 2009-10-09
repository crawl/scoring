CREATE INDEX player_best_game_pscores ON player_best_games (name, sc);
CREATE INDEX wins_name ON wins (name);
CREATE INDEX wins_dur ON wins (dur);
CREATE INDEX wins_turn ON wins (turn);
CREATE INDEX wins_sc ON wins (sc);
CREATE INDEX all_recent_games_end
ON all_recent_games (end_time DESC);
CREATE INDEX player_recent_games_name_end
ON player_recent_games (name, end_time DESC);
CREATE INDEX player_recent_games_name_id
ON player_recent_games (name, id);
CREATE INDEX top_games_sc ON top_games (sc);
CREATE INDEX top_combo_scores_name ON top_combo_scores (name, charabbr);
CREATE UNIQUE INDEX top_combo_scores_charabbr
ON top_combo_scores (charabbr);
CREATE INDEX top_combo_scores_sc ON top_combo_scores (sc);
CREATE UNIQUE INDEX top_species_scores_raceabbr
ON top_species_scores (raceabbr);
CREATE INDEX top_species_scores_name ON top_species_scores (name, crace);
CREATE UNIQUE INDEX top_class_scores_cls
ON top_class_scores (cls);
CREATE INDEX top_class_scores_name ON top_class_scores (name, cls);
CREATE UNIQUE INDEX player_last_games_name
ON player_last_games (name);
CREATE UNIQUE INDEX player_first_games_name
ON player_first_games (name);
CREATE INDEX streak_games_name_time ON streak_games (name, end_time);
CREATE INDEX streaks_order ON streaks (ngames DESC, id);
CREATE INDEX streaks_player ON streaks (player);
CREATE INDEX streaks_player_active ON streaks (player, active);
CREATE INDEX player_total_scores ON players (name, total_score);
CREATE INDEX players_win_stats ON players (games_won DESC, games_played);
CREATE UNIQUE INDEX player_cstats_name_char
                 ON player_char_stats (name, charabbr);
CREATE INDEX player_char_stats_name_cab ON player_char_stats (name, charabbr);
CREATE INDEX top_killers_kills ON top_killers (kills DESC, ckiller);
CREATE INDEX killer_recent_kills_ckiller ON killer_recent_kills (ckiller);
CREATE INDEX ghost_victims_ghost ON ghost_victims (ghost);
CREATE INDEX ghost_victims_victim ON ghost_victims (victim);
CREATE INDEX rune_finds_xl ON low_xl_rune_finds (xl, rune_time);
CREATE INDEX ziggurats_time ON ziggurats (zig_time);
CREATE INDEX date_players_month ON date_players (which_month);