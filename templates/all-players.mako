<%
   import scload, query, crawl_utils, html

   c = attributes['cursor']
 %>
<!DOCTYPE HTML PUBLIC "-//W3C//DTD HTML 4.01//EN"
          "http://www.w3.org/TR/html4/strict.dtd">
<html>
  <head>
    <meta http-equiv="Content-Type" content="text/html; charset=UTF-8">
    <title>All Players</title>
    <link rel="stylesheet" type="text/css" href="score.css">
  </head>


  <body class="page_back">
    <div class="page">
      <%include file="toplink.mako"/>

      <div class="page_content">
        <div class="heading_left">
          <h2>All Players</h2>
        </div>

        <hr>

        <div class="content">
          ${html.all_player_stats(query.all_player_stats(c))}
        </div>
      </div>
    </div>
    ${html.update_time()}
  </body>
</html>
