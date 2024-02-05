<%
   import scload, query, crawl_utils, scoring_html
   c = attributes['cursor']

   stats = query.date_stats(c)
   year_stats = query.date_stats(c, "1 year")
   scoring_html.date_stats(year_stats, "yearly", True)
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
            <h2>Server Activity across official DCSS servers, all time</h2>
            <p>This page updates at most once a day. For monthly stats, see <a href="per-day-monthly.html">here</a>.</p>

            % if scoring_html.MATPLOT and len(stats) > 100:
            <img src="date-stats-all.png" title="All-time online activity"
                 alt="All-time online activity">
            <img src="date-stats-yearly.png" title="Online activity for the last year"
                 alt="Online activity for the last year">
            % endif
                 
            <div style="margin-top: 20px">            
               ${scoring_html.date_stats(stats)}
            </div>
          </div>
        </div>
      </div>
    </div>
    ${scoring_html.update_time()}

  </body>
</html>
