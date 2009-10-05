<%
   import scload, query, crawl_utils, html, re
   c = attributes['cursor']

   n = 100
   fastest_wins = query.find_games(c, 'wins', sort_min='dur', limit=n)
%>
<!DOCTYPE HTML PUBLIC "-//W3C//DTD HTML 4.01//EN"
          "http://www.w3.org/TR/html4/strict.dtd">
<html>
  <head>
    <meta http-equiv="Content-Type" content="text/html; charset=UTF-8">

    <title>The ${n} Fastest Wins (clock time)</title>
    <link rel="stylesheet" type="text/css" href="score.css">
  </head>

  <body class="page_back">
    <div class="page">
      <%include file="toplink.mako"/>

      <div class="page_content">
        <h2>The ${n} Fastest Wins (clock time)</h2>
        ${html.ext_games_table(fastest_wins, first='dur', count=True)}
      </div>
    </div>

    ${html.update_time()}
  </body>
</html>
