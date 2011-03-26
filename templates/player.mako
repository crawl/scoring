<%
   import scload, query, crawl_utils, html

   c = attributes['cursor']
   player = attributes['player']

   ostats = html.overall_player_stats(c, player)
   
   whereis = html.whereis(False, player)
   wins = query.player_wins(c, player)
   streaks = query.player_streaks(c, player, 10)
   recent_games = query.player_recent_games(c, player)

   combo_highscores = query.player_combo_highscores(c, player)
   species_highscores = query.player_species_highscores(c, player)
   class_highscores = query.player_class_highscores(c, player)
   stats = query.player_stats_matrix(c, player)
 %>
<!DOCTYPE HTML PUBLIC "-//W3C//DTD HTML 4.01//EN"
          "http://www.w3.org/TR/html4/strict.dtd">
<html>
  <head>
    <meta http-equiv="Content-Type" content="text/html; charset=UTF-8">

    <title>${player}</title>
    <link rel="stylesheet" type="text/css" href="../score.css">
  </head>

  <body class="page_back">
    <div class="page">
      <%include file="toplink.mako"/>

      <div class="page_content">
        <h2>Player: ${player}</h2>

        <div class="content">

          <h3>Overall Stats</h3>
          ${ostats}
        
          %if whereis:
          <div class="game_table">
            <h3>Ongoing Game (cao)</h3>
            <div class="fineprint">
              On-going information is from the crawl.akrasiac.org server only,
              and may be inaccurate if the player is active on other
              servers.
            </div>
            ${whereis}
          </div>
          %endif

          % if wins:
          <div class="game_table">
            <h3>Wins</h3>
            ${html.player_wins(wins, count=True)}
          </div>
          % endif

          % if streaks:
          <div class="game_table">
            <h3>Streaks of Wins</h3>
            ${html.player_streaks_table(streaks)}
          </div>
          % endif

          <div class="game_table">
            <h3>Recent Games</h3>
            ${html.full_games_table(recent_games, count=False, win=False)}
          </div>

          <hr>

          % if combo_highscores or species_highscores or class_highscores:
            <div>
              ${html.player_scores_block(c, combo_highscores,
                                         'Combo Highscores')}
              ${html.player_scores_block(c, species_highscores,
                                         'Species Highscores')}
              ${html.player_scores_block(c, class_highscores,
                                         'Class Highscores')}
            </div>
            <hr>
          % endif

          <h3>Winning Characters</h3>
          ${html.player_stats_matrix(stats, 'wins')}
          <hr>

          <h3>Games Played</h3>
          ${html.player_stats_matrix(stats, 'games')}
          <hr>

          <h3>Best Character Levels</h3>
          ${html.player_stats_matrix(stats, 'xl')}
          <hr>
        </div>
      </div> <!-- content -->
    </div> <!-- page -->

    ${html.update_time()}
  </body>
</html>
