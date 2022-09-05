<%
   import scload, query, scoring_html
   c = attributes['cursor']

   game_text = \
      scoring_html.ext_games_table( query.get_fastest_turn_player_games(c),
                            first = 'turn', count=True, win=True )
%>

${game_text}
