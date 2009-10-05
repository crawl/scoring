<%
   import scload, query, crawl_utils, html, re
   c = attributes['cursor']

   recent_wins = query.find_games(c, 'wins', sort_max='id', limit=15)
   recent_games = query.find_games(c, 'all_recent_games', sort_max='id',
                                     limit=60)
%>
<!DOCTYPE HTML PUBLIC "-//W3C//DTD HTML 4.01//EN"
          "http://www.w3.org/TR/html4/strict.dtd">
<html>
  <head>
    <meta http-equiv="Content-Type" content="text/html; charset=UTF-8">

    <title>Recent Games</title>
    <link rel="stylesheet" type="text/css" href="score.css">
  </head>

  <body class="page_back">
    <div class="page">
      <%include file="toplink.mako"/>

      <div class="page_content">
        <h2>Recent Wins</h2>
        ${html.ext_games_table(recent_wins, win=True)}

        <h2>Recent Games</h2>
        ${html.ext_games_table(recent_games)}
      </div>
    </div>

    ${html.update_time()}
  </body>
</html>
