<%
   import loaddb, query, crawl_utils, html

   c = attributes['cursor']
   player = attributes['player']

   whereis = html.whereis(False, player)
 %>
<!DOCTYPE HTML PUBLIC "-//W3C//DTD HTML 4.01//EN"
          "http://www.w3.org/TR/html4/strict.dtd">
<html>
  <head>
    <meta http-equiv="Content-Type" content="text/html; charset=UTF-8">

    <title>${player}</title>
    <link rel="stylesheet" type="text/css" href="../tourney-score.css">
  </head>

  <body class="page_back">
    <div class="page bannered">
      <%include file="toplink.mako"/>

      <div class="page_content">
        <h2>Player: ${player}</h2>

        <div class="content">

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

          <div class="game_table">
            <h3>Wins</h3>
            ${html.full_games_table(won_games, count=False)}
          </div>

          % if streak_games:
          <div class="game_table">
            <h3>Longest streak of wins</h3>
            ${html.full_games_table(streak_games)}
          </div>
          % endif

          % if won_gods:
          <div id="won-gods">
            <h3>Winning Gods:</h3>
            <div class="bordered inline">
              ${", ".join(won_gods)}
            </div>

            <p class="fineprint">
              All gods that ${player} has won games with, without changing
              gods (or renouncing and rejoining gods) during the game.
            </p>

            <h3>Remaining Gods:</h3>
            <div class="bordered inline">
              ${", ".join(query.find_remaining_gods(won_gods)) or 'None'}
            </div>
          </div>
          % endif

          <div class="game_table">
            <h3>Recent Games</h3>
            ${html.full_games_table(recent_games, count=False, win=False)}
          </div>

          <hr>

          % if uniq_slain:
          <div>
            <table class="bordered">
              <colgroup>
                 <col width="10%">
                 <col width="85%">
              </colgroup>
              <tr>
                <th>Uniques Slain</th>
                <td>${", ".join(uniq_slain)}</td>
              </tr>
              % if len(uniq_slain) > len(uniq_unslain):
                <tr>
                  <th>Uniques Left</th>
                  % if uniq_unslain:
                  <td>${", ".join(uniq_unslain)}</td>
                  % else:
                  <td>None</td>
                  % endif
                </tr>
              % endif
            </table>
          </div>
          <hr>
          % endif

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

          <div class="audit_table">
            <h3>Score Breakdown</h3>
            <table class="grouping">
              <tr>
                <td>
                  <h4>Player points</h4>
                  <table class="bordered">
                    <tr>
                      <th>N</th> <th>Points</th> <th>Source</th>
                    </tr>
                    ${point_breakdown(audit)}
                  </table>
                </td>

                <td>
                  <h4>Team points</h4>
                  <table class="bordered">
                    <tr>
                      <th>N</th> <th>Points</th> <th>Source</th>
                    </tr>
                    ${point_breakdown(audit_team)}
                  </table>
                </td>

                <td class="legend">
                  <h4>Legend</h4>
                  <table class="bordered">
                    <tr class="point_perm">
                      <td>Permanent points</td>
                    </tr>
                    <tr class="point_temp">
                      <td>Provisional points</td>
                    </tr>
                  </table>
                </td>
              </tr>
            </table>
          </div>
        </div>
      </div> <!-- content -->
    </div> <!-- page -->

    ${html.update_time()}
  </body>
</html>
