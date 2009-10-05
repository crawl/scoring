<%
   import scload, query, html
   c = attributes['cursor']

   game_text = \
      html.ext_games_table( query.get_fastest_time_player_games(c),
                            first = 'dur', count=True, win=True )
%>

${game_text}
