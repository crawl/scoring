<%
   import scload, query, crawl_utils, html, re
   c = attributes['cursor']

   gkills = query.gkills(c)
   gvictims = query.gvictims(c)

   table = html.table_text([ 'Ghost', 'Kills', 'Victims' ],
                           gkills)

   vtable = html.table_text([ 'Victim', 'Deaths', 'Vengeful Spirits' ],
                           gvictims)
%>
<!DOCTYPE HTML PUBLIC "-//W3C//DTD HTML 4.01//EN"
          "http://www.w3.org/TR/html4/strict.dtd">
<html>
  <head>
    <meta http-equiv="Content-Type" content="text/html; charset=UTF-8">

    <title>Ghosts in the Machine</title>
    <link rel="stylesheet" type="text/css" href="score.css">
  </head>

  <body class="page_back">
    <div class="page">
      <%include file="toplink.mako"/>

      <div class="page_content">
        <h2>Marauding Ghosts</h2>
        ${table}
        <hr>
        <h2>Victims</h2>
        ${vtable}
      </div>
    </div>

    ${html.update_time()}
  </body>
</html>
