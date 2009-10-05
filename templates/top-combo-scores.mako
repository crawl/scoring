<%
   import scload, query, crawl_utils, html
   c = attributes['cursor']

   top_combo_scores = query.top_combo_scores(c)
%>
<!DOCTYPE HTML PUBLIC "-//W3C//DTD HTML 4.01//EN"
          "http://www.w3.org/TR/html4/strict.dtd">
<html>
  <head>
    <meta http-equiv="Content-Type" content="text/html; charset=UTF-8">

    <title>Top Combo Scores</title>
    <link rel="stylesheet" type="text/css" href="score.css">
  </head>

  <body class="page_back">
    <div class="page">
      <%include file="toplink.mako"/>

      <div class="page_content">
        <div class="content">

          <h2>Top Combo Scores</h2>

          <div class="fineprint" style="margin-bottom: 4px">
            The best scoring games for each character combo.
          </div>

          ${html.top_combo_scores(top_combo_scores)}
        </div>
      </div>
    </div>

    ${html.update_time()}
  </body>
</html>
