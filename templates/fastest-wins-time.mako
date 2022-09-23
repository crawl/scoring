<%
    import scload, query, crawl_utils, scoring_html, re
    c = attributes['cursor']

    n = 100
    all_fastest_wins = query.find_games(c, 'wins', sort_min='dur', limit=n,
                                                    exclude_name='botnames')
    by_version = query.find_games_by_vclean(c, 'wins', sort_min='dur', limit=n,
                                                    exclude_name='botnames')
    tab_order = query.get_clean_versions(c)
    # insert after trunk
    tab_order = tab_order[:2] + ["all"] + tab_order[2:]
    by_version["all"] = all_fastest_wins
%>
<!DOCTYPE HTML PUBLIC "-//W3C//DTD HTML 4.01//EN"
          "http://www.w3.org/TR/html4/strict.dtd">
<html>
  <head>
    <meta http-equiv="Content-Type" content="text/html; charset=UTF-8">

    <title>Fastest wins by version (clock time)</title>
    <link rel="stylesheet" type="text/css" href="score.css">
  </head>
  <script src="scoring.js"></script>

  <body class="page_back" onload="init_version_tabs('current')">
    <div class="page">
      <%include file="toplink.mako"/>

      <div class="tab" id="version_buttons">
      % for v in tab_order:
        <a class="tablinks" id='button_${v}' href="#${v}" onclick="click_handler(event, '${v}')">${query.pretty_vclean(v, False)}</a>
      % endfor
      </div>

      <div class="page_content">
        <h2>Fastest wins by version (clock time)</h2>

      % for v in tab_order:
        <div class="game_table" id="${v}">
          <h3>${query.pretty_vclean(v)}</h3>
          ${scoring_html.ext_games_table(by_version[v], first='dur', count=True)}
        </div>
      % endfor

      </div>
    </div>

    ${scoring_html.update_time()}
  </body>
</html>
