<%
   import query, scload, html
   c = attributes['cursor']

   top_scores = query.find_games(c, 'top_games', sort_max='sc', limit=5)

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
          <h1>${html.TITLE}</h1>
        </div>
        <hr>

        <div class="content">

          <div class="row">
            <div>
              <h3>Recent Wins</h3>
              ${html.ext_games_table(query.recent_wins(c), win=True)}
            </div>
            <div>
	          <h3>Recent All-Rune Wins</h3>
              ${html.ext_games_table(query.recent_allrune_wins(c), win=True)}
            </div>
          </div>

          <hr>
          
          <div class="row">
            <div>
              <h3>Top Scores</h3>
              ${html.ext_games_table(top_scores, count=True)}
            </div>
            <div>
              <h3>Fastest Wins (Turn Count)</h3>
              <%include file="fastest-turn.mako"/>
            </div>
            <div>
              <h3>Fastest Wins (Real Time)</h3>
              <%include file="fastest-time.mako"/>
            </div>
          </div>

          <hr>

          <div class="row">
            <div>
	          <h3>Best Streaks</h3>
              ${html.all_streaks_table(streaks[:10])}
            </div>

            <div>
              <h3>Active Streaks</h3>
              ${html.all_streaks_table(active_streaks[:10], active=True)}
            </div>
          </div>

          <hr>

          <div class="row">
            <div>
              <h3>Most High Scores</h3>
              ${html.combo_highscorers(c)}
            </div>
          </div>

          <hr>

          <div class="row">
            <div>
              <h3>Ziggurat Raiders</h3>
              ${html.best_ziggurats(c)}
            </div>

            <div>
              <h3>Runes Fetched at Lowest XL</h3>
              ${html.youngest_rune_finds(c)}
              <p class="fineprint">
                Note: the abyssal rune is not eligible.
              </p>
            </div>

            <div>
              <h3>Most Pacific Wins</h3>
              ${html.most_pacific_wins(c)}
              <p class="fineprint">
                Winning games with the fewest slain creatures.
              </p>
            </div>
          </div>

        </div> <!-- Content -->
      </div>
    </div>
    ${html.update_time()}
  </body>
</html>
