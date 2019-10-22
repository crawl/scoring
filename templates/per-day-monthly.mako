<%
   import scload, query, crawl_utils, html
   c = attributes['cursor']

   stats = query.date_stats(c, True)
%>
<!DOCTYPE HTML PUBLIC "-//W3C//DTD HTML 4.01//EN"
          "http://www.w3.org/TR/html4/strict.dtd">
<html>
  <head>
    <meta http-equiv="Content-Type" content="text/html; charset=UTF-8">

    <title>Server Activity</title>
    <link rel="stylesheet" type="text/css" href="score.css">
  </head>

  <body class="page_back">
    <div class="page">
      <%include file="toplink.mako"/>

      <div class="page_content">
        <div class="content">

          <div>
            <h2>Server Activity across official DCSS servers during the last month</h2>

            <p>For all-time stats, see <a href="per-day.html">here</a>.</p>

            % if html.MATPLOT:
            <p><img src="date-stats-monthly.png" title="Activity Graph"
                 alt="Server Activity Graph"></p>
            % endif
                 
            <div style="margin-top: 20px">            
               ${html.date_stats(stats, "-monthly")}
            </div>
          </div>
        </div>
      </div>
    </div>

    ${html.update_time()}
  </body>
</html>
