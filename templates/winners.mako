<%
   import scload, query, crawl_utils, html, re
   c = attributes['cursor']

   winners = query.winner_stats(c)
%>
<!DOCTYPE HTML PUBLIC "-//W3C//DTD HTML 4.01//EN"
          "http://www.w3.org/TR/html4/strict.dtd">
<html>
  <head>
    <meta http-equiv="Content-Type" content="text/html; charset=UTF-8">

    <title>Winner Statistics</title>
    <link rel="stylesheet" type="text/css" href="score.css">
  </head>

  <body class="page_back">
    <div class="page">
      <%include file="toplink.mako"/>

      <div class="page_content">
        <h2>Winner Statistics</h2>
        ${html.winner_stats(winners)}
      </div>
    </div>

    ${html.update_time()}
  </body>
</html>
