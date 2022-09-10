function select_tab(tab_id)
{
    var tabcontent = document.getElementsByClassName("game_table");
    var found = false;
    for (var i = 0; i < tabcontent.length; i++)
    {
        if (tabcontent[i].id == tab_id)
        {
            tabcontent[i].style.display = "block"
            found = true;
        }
        else
            tabcontent[i].style.display = "none";
    }
    if (!found)
        return false;

    var tablinks = document.getElementsByClassName("tablinks");
    for (var i = 0; i < tablinks.length; i++)
        tablinks[i].className = tablinks[i].className.replace(" active", "");
    document.getElementById("button_" + tab_id).className += " active";

    window.scrollTo(0, 0);
    // should not trigger `hashchange`, per spec!
    history.replaceState(undefined, undefined, "#" + tab_id);
    return true;
}

function click_handler(e, tab_id)
{
    select_tab(tab_id);
    // keep the actual anchor value from doing anything. Having it set but
    // prevented this way lets the buttons still work if there is no javascript.
    e.preventDefault();
}

function load_from_hash(default_tab)
{
    if (!window.location.hash || !select_tab(window.location.hash.substring(1)))
        select_tab(default_tab);
}

function init_version_tabs(default_tab)
{
    // call this in onload

    // prereqs: a set of divs of class `game_table` with ids, and
    // a set of buttons of class `tablinks` with ids `button_X`,
    // for every tab id X. You also need to set up the click handlers
    // for the buttons.

    load_from_hash(default_tab);
    // hacky: chrome workaround
    setTimeout(function() { window.scrollTo(0,0); }, 1);
    addEventListener('hashchange', e => { load_from_hash(default_tab); });
}
