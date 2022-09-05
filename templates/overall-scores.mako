<%
   import scload, query, scoring_html
   c = attributes['cursor']

   text = scoring_html.table_text( [ 'Player', 'Points' ],
                           query.get_top_players(c),
                           place_column=1 )
%>

${text}
