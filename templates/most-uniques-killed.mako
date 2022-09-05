<%
   import scload, query, scoring_html
   c = attributes['cursor']

   text = scoring_html.table_text( [ 'Player', 'Uniques Slain' ],
                           query.get_top_unique_killers(c) )
%>

${text}
