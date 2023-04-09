<%
   import scload, query, crawl_utils, scoring_html
   c = attributes['cursor']

   top_scores = query.simplified_score_ordering(c)
%>
<!DOCTYPE HTML PUBLIC "-//W3C//DTD HTML 4.01//EN"
          "http://www.w3.org/TR/html4/strict.dtd">
<html>
  <head>
    <meta http-equiv="Content-Type" content="text/html; charset=UTF-8">

    <title>Players Ranked by Total Score</title>
    <link rel="stylesheet" type="text/css" href="score.css">
  </head>

  <body class="page_back">
    <div class="page">
      <%include file="toplink.mako"/>

      <div class="page_content">
        <div class="content">

          <div>
            <h2>Active players Ranked by Total Score</h2>

            <p>This page shows only accounts that have been active in the last six months. See <a href="best-players-all-total-score.html">here</a> for the all-time listing.</p>

            ${scoring_html.best_players_by_total_score(top_scores)}
          </div>
        </div>
      </div>
    </div>

    ${scoring_html.update_time()}
  </body>
</html>
