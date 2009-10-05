<%

   import scload, query, crawl_utils, html, combos
   c = attributes['cursor']

%>
<!DOCTYPE HTML PUBLIC "-//W3C//DTD HTML 4.01//EN"
          "http://www.w3.org/TR/html4/strict.dtd">
<html>
  <head>
    <meta http-equiv="Content-Type" content="text/html; charset=UTF-8">
    <title>Combo Scoreboard</title>
    <link rel="stylesheet" type="text/css" href="score.css">
  </head>

  <body class="page_back">
    <div class="page">
      <%include file="toplink.mako"/>

      <div class="page_content">
        <h2>Species Highscorers</h2>
        ${html.top_species_scorers(query.top_species_scorers(c))}

        <h2>Class Highscorers</h2>
        ${html.top_class_scorers(query.top_class_scorers(c))}

        <h2>Combo Highscorers</h2>
        ${html.top_combo_scorers(query.top_combo_scorers(c))}
      </div>
    </div>

    ${html.update_time()}
  </body>
</html>
