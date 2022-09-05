<%
   import crawl_utils, scload, query, scoring_html
   c = attributes['cursor']
%>
<!DOCTYPE HTML PUBLIC "-//W3C//DTD HTML 4.01//EN"
          "http://www.w3.org/TR/html4/strict.dtd">
<html>
  <head>
    <meta http-equiv="Content-Type" content="text/html; charset=UTF-8">

    <title>Clans</title>
    <link rel="stylesheet" type="text/css" href="score.css">
  </head>
  <body class="page_back">
    <div class="page">
      <%include file="toplink.mako"/>
      <div class="page_content">
        <%
           teams = \
              query.query_rows(c,
                               '''SELECT total_score, name, owner
                                  FROM teams
                                  ORDER BY total_score DESC, name''')
           teams = [ list(x) for x in teams ]

           for team in teams:
             captain = team.pop()
             team[1] = scoring_html.linked_text(captain, crawl_utils.clan_link,
                                        team[1])
             team.append( scoring_html.clan_affiliation(c, captain, False) )

           table = scoring_html.table_text( [ 'Score', 'Clan', 'Players' ],
                                    teams, cls='bordered', place_column=0 )
        %>

        <h1>Clans</h1>
        <hr>
        <div class="content">
          ${table}
        </div>
      </div>
    </div>
    ${scoring_html.update_time()}
  </body>
</html>
