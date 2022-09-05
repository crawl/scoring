<%
   import query, scload, scoring_html, config
   c = attributes['cursor']

   top_scores = query.find_games(c, 'top_games', sort_max='sc', limit=10)
   ts_wins = all([g.get('ktyp') == 'winning' for g in top_scores])

   cur_top_scores = query.find_games(c, 'top_games', sort_max='sc', vtriage=True, vclean='current', limit=10)
   cur_ts_wins = all([g.get('ktyp') == 'winning' for g in cur_top_scores])

   cur_time_wins = query.get_fastest_time_player_games(c, current=True)
   cur_tc_wins = query.get_fastest_turn_player_games(c, current=True)
   time_wins = query.get_fastest_time_player_games(c)
   tc_wins = query.get_fastest_turn_player_games(c)

   streaks = query.all_streaks(c)
   active_streaks = query.all_streaks(c, active_streaks=True)
%>
<!DOCTYPE HTML PUBLIC "-//W3C//DTD HTML 4.01//EN"
          "http://www.w3.org/TR/html4/strict.dtd">
<html>
  <%include file="head.mako"/>
  <body class="page_back">
    <div class="page">
      <%include file="toplink.mako"/>
      <div class="page_content">
        <div class="heading">
          <h1>${scoring_html.TITLE}</h1>
        </div>
        <hr>

        <div class="content">

          <div class="row">
            <div>
              <h3>Recent Wins</h3>
              ${scoring_html.ext_games_table(query.recent_wins(c), win=True)}
            </div>
            <div>
	          <h3>Recent All-Rune Wins</h3>
              ${scoring_html.ext_games_table(query.recent_allrune_wins(c), win=True)}
            </div>
          </div>

          <hr>

          <div class="row">
            <div>
              <h3>Top Scores (current stable version)</h3>
              ${scoring_html.ext_games_table(cur_top_scores, win=cur_ts_wins, count=True)}
            </div>
            <div>
              <h3>Fastest Wins by Turn Count (current stable version)</h3>
              ${scoring_html.ext_games_table(cur_tc_wins, first='turn', win=True, count=True)}
            </div>
            <div>
              <h3>Fastest Wins by Time (current stable version)</h3>
              ${scoring_html.ext_games_table(cur_time_wins, first='dur', win=True, count=True)}
            </div>
          </div>

          <hr>
          
          <div class="row">
            <div>
              <h3>Top Scores (all time)</h3>
              ${scoring_html.ext_games_table(top_scores, win=ts_wins, count=True)}
            </div>
            <div>
              <h3>Fastest Wins by Turn Count (all time)</h3>
              ${scoring_html.ext_games_table(tc_wins, first='turn', win=True, count=True)}
            </div>
            <div>
              <h3>Fastest Wins by Time (all time)</h3>
              ${scoring_html.ext_games_table(time_wins, first='dur', win=True, count=True)}
            </div>
          </div>

          <hr>

          <div class="row">
            <div>
	          <h3>Best Streaks</h3>
              ${scoring_html.all_streaks_table(streaks[:10])}
            </div>

            <div>
              <h3>Active Streaks</h3>
              ${scoring_html.all_streaks_table(active_streaks[:10], active=True)}
            </div>
          </div>

          <hr>

          <div class="row">
            <div>
              <h3>Most High Scores</h3>
              ${scoring_html.combo_highscorers(c)}
            </div>
          </div>

          <hr>

          <div class="row">
            % if config.USE_MILESTONES:
            <div>
              <h3>Ziggurat Raiders</h3>
              ${scoring_html.best_ziggurats(c)}
            </div>

            <div>
              <h3>Runes Fetched at Lowest XL</h3>
              ${scoring_html.youngest_rune_finds(c)}
              <p class="fineprint">
                Note: the abyssal rune is not eligible.
              </p>
            </div>
            % endif

            <div>
              <h3>Most Pacific Wins</h3>
              ${scoring_html.most_pacific_wins(c)}
              <p class="fineprint">
                Winning games with the fewest slain creatures.
              </p>
            </div>
          </div>

        </div> <!-- Content -->
      </div>
    </div>
    ${scoring_html.update_time()}
  </body>
</html>
