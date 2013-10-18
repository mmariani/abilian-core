{%- set locale = get_locale() %}
(function($) {

$(document).ready(Abilian.init);
window.onbeforeprint = Abilian.fn.before_print;

Abilian.DEBUG = {{ config.DEBUG|tojson }};
Abilian.locale = {{ locale.language|tojson }};

bootbox.setDefaults({ 'locale': Abilian.locale });

{#- load select2 locale file #}
Abilian.fn.loadScript('{{ url_for('abilian_static', filename='select2/select2_locale_' + locale.language + '.js') }}');

{#- bootstrap-datepicker locale #}
Abilian.fn.loadScript('{{ url_for('abilian_static', filename='bootstrap-datepicker/js/locales/bootstrap-datepicker.' + locale.language + '.js') }}');

Abilian.datepicker_defaults = {
    'todayHighlight': true,
    'todayBtn': true,
    'language': {{ locale.language|tojson }},
    {#- first week day: for babel 0 == Monday, datetimepicker 0 == Sunday #}
    'weekStart': {{ ((locale.first_week_day + 1) % 7)|tojson }}
};

{#- timepicker: set 12/24 time #}
{%- set short_time = locale.time_formats['short'].pattern %}
Abilian.timepicker_defaults = { 'showMeridian': {{ ('h' in short_time or 'k' in short_time)|tojson }} };

}(jQuery));