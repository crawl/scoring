<%
   import loaddb, query, html
   c = attributes['cursor']

   game_text = \
      html.ext_games_table( query.get_fastest_turn_player_games(c),
                            first = 'turn', count=True )
%>

${game_text}
