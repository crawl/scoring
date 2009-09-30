<%
   import loaddb, query, crawl_utils, html
   c = attributes['cursor']

   top_scores = query.find_games(c, 'top_games')
%>
<!DOCTYPE HTML PUBLIC "-//W3C//DTD HTML 4.01//EN"
          "http://www.w3.org/TR/html4/strict.dtd">
<html>
  <head>
    <meta http-equiv="Content-Type" content="text/html; charset=UTF-8">

    <title>Top Scores</title>
    <link rel="stylesheet" type="text/css" href="tourney-score.css">
  </head>

  <body class="page_back">
    <div class="page">
      <%include file="toplink.mako"/>

      <div class="page_content">
        <div class="content">

          <hr style="width: 50%; margin-left: 0px;">
          <div>
            <h2>Top Scores</h2>

            ${html.ext_games_table(top_scores)}
          </div>
        </div>
      </div>
    </div>

    ${html.update_time()}
  </body>
</html>
