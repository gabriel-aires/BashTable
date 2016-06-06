#!/bin/bash

### Inicialização
source $(dirname $(dirname $(dirname $(readlink -f $0))))/common/sh/include.sh || exit 1
source $install_dir/sh/include.sh || exit 1

function end() {
    test "$1" == "0" || echo "      <p><b>Operação inválida.</b></p>"
    web_footer

    if [ -n "$tmp_dir" ] && [ -d "$tmp_dir" ]; then
        rm -f $tmp_dir/*
        rmdir $tmp_dir
    fi

    test -n "$sleep_pid" && kill "$sleep_pid" &> /dev/null
    clean_locks
    wait &> /dev/null

    exit $1
}

function display_faq() {

    test -f $tmp_dir/results || return 1

    echo "<div class=\"column_large\" id=\"faq_topics\">"

    local error=0
    local content_file="$(head -n 1 $tmp_dir/results | sed -r "s|^([^;]*);([^;]*);([^;]*);[^;]*;$|\1\%\2\%\3\%|")"

    sed -i -r "s|^$faq_dir_tree/||" $tmp_dir/results
    sed -i -r "s|^([^;]*);([^;]*);([^;]*);([^;]*);$|<a_href=\"$start_page\?category=\1\&proceed=$proceed_search\">\1</a>;<a_href=\"$start_page\?category=\1\&question=\2\&proceed=$proceed_view\">\4</a>;\3;|" $tmp_dir/results

    while grep -Ex "([^;]*;){2}(<a_href.*/a> )?$regex_faq_tag [^;]*;" $tmp_dir/results > /dev/null; do
        sed -i -r "s|^(([^;]*;){2}(<a_href.*/a> )?)($regex_faq_tag) ([^;]*;)$|\1<a_href=\"$start_page\?tag=\4\&proceed=$proceed_search\">\4</a> \5|" $tmp_dir/results
    done

    sed -i -r "s|^(([^;]*;){2}(<a_href.*/a> )?)($regex_faq_tag);$|\1<a_href=\"$start_page\?tag=\4\&proceed=$proceed_search\">\4</a>;|" $tmp_dir/results

    while grep -E "<a_href=\"$start_page\?[^\"]*/[^\"]*\">" $tmp_dir/results > /dev/null; do
        sed -i -r "s|(<a_href=\"$start_page\?[^\"]*)/([^\"]*\">)|\1\%2F\2|" $tmp_dir/results
    done

    sed -i -r "s|<a_href=|<a href=|g" $tmp_dir/results

    if [ $(cat $tmp_dir/results | wc -l) -eq 1 ]; then

        category_href="$(sed -r "s|^([^;]*);[^;]*;[^;]*;$|\1|" $tmp_dir/results)"
        tag_href="$(sed -r "s|^[^;]*;[^;]*;([^;]*);$|\1|" $tmp_dir/results)"

        echo "<h3>"
        head -n 1 "$content_file"
        echo "</h3>"
        echo "<div class=\"cfg_color\">"
        echo "  <pre>"
        tail -n +2 "$content_file"
        echo "  </pre>"
        echo "</div>"
        echo "<p><b>Categoria:</b> $category_href</p>"
        echo "<p><b>Tags:</b> $tag_href</p>"

    elif [ $(cat $tmp_dir/results | wc -l) -ge 2 ]; then

        sed -i -r "s|^([^;]*;)([^;]*;)([^;]*;)$|\2\1\3|" $tmp_dir/results
        sed -i -r "s|;|</td><td>|g" $tmp_dir/results
        sed -i -r "s|^(.)|<tr class=\"cfg_color\"><td width=80%>\1|" $tmp_dir/results
        sed -i -r "s|<td>$|</tr>|" $tmp_dir/results

        echo "<table id=\"faq\" width=100%>"
        echo "<tr class=\"header_color\"><td width=80%>Tópico</td><td>Categoria</td><td>Tags</td></tr>"
        cat $tmp_dir/results
        echo "</table>"

    else

        echo "<p>Sua busca não retornou resultados.</p>"
        error=1

    fi

    echo "</div>"

    return "$error"

}

trap "end 1" SIGQUIT SIGINT SIGHUP
mkdir $tmp_dir

# Cabeçalho
web_header

test -d "$faq_dir_tree" || end 1

proceed_search="Buscar"
proceed_view="Exibir"
proceed_new="Novo"
proceed_edit="Editar"

regex_faq_question="[a-zA-Z0-9][a-zA-Z0-9 \.\?\!_,-]*"
regex_faq_tag="[a-zA-Z0-9\.-]+"

# listas de tópicos, categorias e tags
find $faq_dir_tree/ -mindepth 2 -type f | xargs -I{} grep -m 1 -H ".*" {} | tr -d ":" | sed -r "s|(.)$|\1\%|"> $tmp_dir/questions.list
find $faq_dir_tree/ -mindepth 1 -type d | sed -r "s|^$faq_dir_tree/||" | sort > $tmp_dir/categories.list
cut -d '%' -f 3 $tmp_dir/questions.list | tr " " "\n" | sort | uniq > $tmp_dir/tags.list

# Formulário de pesquisa
echo "      <div class=\"column_small\" id=\"faq_sidebar\">"
echo "          <h3>Busca:</h3>"
echo "          <form action=\"$start_page\" method=\"get\">"
echo "              <p>"
echo "                  <select class=\"select_large_percent\" name=\"category\">"
echo "                          <option value=\"\" selected>Categoria...</option>"
sed -r "s|(.*)|\t\t\t\t\t<option>\1</option>|" $tmp_dir/categories.list
echo "                  </select>"
echo "              </p>"
echo "              <p>"
echo "                  <select class=\"select_large_percent\" name=\"tag\">"
echo "                          <option value=\"\" selected>Tag...</option>"
sed -r "s|(.*)|\t\t\t\t\t<option>\1</option>|" $tmp_dir/tags.list
echo "                  </select>"
echo "              </p>"
echo "              <p>"
echo "                  <input type=\"text\" class=\"text_large_percent\" placeholder=\" Pesquisar...\" name=\"search\"></input>"
echo "              </p>"
echo "              <p>"
echo "                  <input type=\"submit\" name=\"proceed\" value=\"$proceed_search\">"
echo "              </p>"
echo "          </form>"
echo "      </div>"

parsed=false
var_string=false

if [ "$REQUEST_METHOD" == "POST" ]; then

    if [ "$CONTENT_TYPE" == "application/x-www-form-urlencoded" ]; then
        test -n "$CONTENT_LENGTH" && read -n "$CONTENT_LENGTH" POST_STRING
        var_string=true
        arg_string="&$(web_filter "$POST_STRING")&"

    elif echo "$CONTENT_TYPE" | grep -Ex "multipart/form-data; +boundary=.*" > /dev/null; then
        cat > "$tmp_dir/POST_CONTENT"
        parse_multipart_form "$tmp_dir/POST_CONTENT"
        rm -f "$tmp_dir/POST_CONTENT"
    fi

else
    var_string=true
    arg_string="&$(web_filter "$QUERY_STRING")&"
fi

if $var_string; then
    category=$(echo "$arg_string" | sed -rn "s/^.*&category=([^\&]+)&.*$/\1/p")
    tag=$(echo "$arg_string" | sed -rn "s/^.*&tag=([^\&]+)&.*$/\1/p")
    question=$(echo "$arg_string" | sed -rn "s/^.*&question=([^\&]+)&.*$/\1/p")
    search=$(echo "$arg_string" | sed -rn "s/^.*&search=([^\&]+)&.*$/\1/p")
    proceed=$(echo "$arg_string" | sed -rn "s/^.*&proceed=([^\&]+)&.*$/\1/p")
fi

test -n "$proceed" && parsed=true

if ! $parsed; then

    query_file.sh -d "%" -r ";" -s 1 2 3 4 -f $tmp_dir/questions.list -o 1 4 asc > $tmp_dir/results
    display_faq

else

    case "$proceed" in

        "$proceed_search")

            where=''

            test -n "$search" && find $faq_dir_tree/ -mindepth 2 -type f | xargs -I{} grep -ilF "$search" {} | xargs -I{} grep -m 1 -H ".*" {} | tr -d ":" | sed -r "s|(.)$|\1\%|"> $tmp_dir/questions.list
            test -n "$category" && category_aux="$(echo "$category" | sed -r 's|([\.-])|\\\1|g;s|/$||')" && where="$where 1=~$faq_dir_tree/${category_aux}/.*"
            test -n "$tag" && tag_aux="$(echo "$tag" | sed -r 's|([\.-])|\\\1|g')" && where="$where 3=~(.+[[:blank:]])*${tag_aux}([[:blank:]].+)*"
            test -n "$where" && where="-w $where"

            query_file.sh -d "%" -r ";" \
                -s 1 2 3 4 \
                -f $tmp_dir/questions.list \
                $where \
                -o 1 4 asc \
                > $tmp_dir/results

            display_faq

        ;;

        "$proceed_view")

            query_file.sh -d "%" -r ";" \
                -s 1 2 3 4 \
                -f $tmp_dir/questions.list \
                -w "1=~$faq_dir_tree/$(echo "$category" | sed -r 's|([\.-])|\\\1|g;s|/$||')/" "2==$(echo "$question" | sed -r 's|([\.-])|\\\1|g')" \
                -o 1 4 asc \
                > $tmp_dir/results

            display_faq

        ;;

        "$proceed_new") ;;
        "$proceed_edit") ;;
        *) echo "Operação inválida." ;;

    esac

fi

end 0
