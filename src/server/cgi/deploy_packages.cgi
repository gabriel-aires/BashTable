#!/bin/bash

### Inicialização
source $(dirname $(dirname $(dirname $(readlink -f $0))))/common/sh/include.sh || exit 1
source $install_dir/sh/include.sh || exit 1

function parse_multipart_form() { #argumentos: nome de arquivo com conteúdo do POST, boundary

    #atribui variáveis do formulário e prepara arquivos carregados para o servidor

    local boundary="$(echo "$CONTENT_TYPE" | sed -r "s|multipart/form-data; +boundary=||" | sed -r 's|\-|\\-|g')"
    local part_boundary="\-\-$boundary"
    local end_boundary="\-\-$boundary\-\-"
    local next_boundary=''
    local input_file="$1"
    local input_size="$(cat "$input_file" | wc -l)"
    local file_begin=''
    local file_end=''
    local file_cmd=()
    local file_name=''
    local var_name=''
    local var_set=false
    local i=0
    local n=0

    while [ "$i" -lt "$input_size" ]; do

        ((i++))

        line="$(sed -n "${i}p" "$input_file" | sed -r "s|\r$||")"

        echo "<b>||debug||<br>"

        if echo "$line" | grep -Ex "$part_boundary|$end_boundary" > /dev/null; then

            file_name=''
            file_begin=''
            file_end=''
            var_name=''
            var_set=false

            echo "  match: boundary_line"

        elif echo "$line" | grep -Ex "Content\-Disposition: form\-data; name=[^;]*; filename=.*" > /dev/null; then

            var_name="$(echo "$line" | sed -r "s|Content\-Disposition: form\-data; name=([^;]*); filename=.*|\1|" | sed -r "s|\"||g")"
            file_name="$(echo "$line" | sed -r "s|Content\-Disposition: form\-data; name=[^;]*; filename=||" | sed -r "s|\"||g")"
            file_name="$tmp_dir/$(basename $file_name)"
            eval "$var_name=$file_name"
            var_set=true
            file_begin=$((i+3)) #i+1: content-type, i+2: '', i+3: file_begin
            next_boundary=$(sed -n "${file_begin},${input_size}p" "$input_file" | cat -t | grep -En "^$part_boundary" | head -n 1 | cut -d ':' -f1)
            next_boundary=$((next_boundary+file_begin))
            file_end=$((next_boundary-1))
            i="$file_end"
            file_cmd[$n]="sed -n '${file_begin},${file_end}p' $input_file > $file_name"
            ((n++))

            echo "  match: file_line"

        elif echo "$line" | grep -Ex "Content\-Disposition: form\-data; name=.*" > /dev/null; then

            var_name="$(echo "$line" | sed -r "s|Content\-Disposition: form\-data; name=||" | sed -r "s|\"||g")"

            echo "  match: param_line"

        elif [ -n "$line" ]; then

            ! $var_set && test -n "$var_name" && eval "$var_name=$line" && var_set=true

            echo "  match: value_line"

        fi

        #DEBUG
        echo "  <br>"
        echo "  boundary: $boundary<br>"
        echo "  part_boundary: $part_boundary<br>"
        echo "  end_boundary: $end_boundary<br>"
        echo "  text_line: $(echo "$line" | cat -t)<br>"
        echo "  num_line: $i<br>"
        echo "  var_name: $var_name<br>"
        echo "  var_set: $var_set<br>"
        echo "  input_size: $input_size<br>"
        echo "  file_name: $file_name<br>"
        echo "  file_begin: $file_begin<br>"
        echo "  file_end: $file_end<br>"
        echo "  file_cmd: ( ${file_cmd[*]} )<br>"
        echo '||/debug||</b><br><br>'
        #DEBUG

    done

    if [ $n -gt 0 ]; then
        for i in $(seq 0 $n); do
            test -n "${file_cmd[$i]}" && eval ${file_cmd[$i]}
        done
    fi

}

function submit_deploy() {

    if [ "$proceed" != "$proceed_view" ]; then
        return 1

    else
        local app_deploy_clearance="$tmp_dir/app_deploy_clearance"
        local env_deploy_clearance="$tmp_dir/env_deploy_clearance"
        local process_group=''
        local show_form=false

        rm -f $app_deploy_clearance $env_deploy_clearance

        { clearance "user" "$REMOTE_USER" "app" "$app_name" "write" && touch "$app_deploy_clearance"; } &
        process_group="$process_group $!"

        { clearance "user" "$REMOTE_USER" "ambiente" "$env_name" "write" && touch "$env_deploy_clearance"; } &
        process_group="$process_group $!"

        wait $process_group
        test -f $app_deploy_clearance && test -f $env_deploy_clearance && show_form=true

        if $show_form; then
            echo "      <p>"
            echo "          <form action=\"$start_page\" method=\"post\" enctype=\"multipart/form-data\">"
            echo "              <input type=\"hidden\" name=\"$app_param\" value=\"$app_name\"></td></tr>"
            echo "              <input type=\"hidden\" name=\"$env_param\" value=\"$env_name\"></td></tr>"
            echo "              <input type=\"submit\" name=\"proceed\" value=\"$proceed_deploy\">"
            echo "              Arquivo: <input type=\"file\" name=\"file\">"
            echo "              <input type=\"submit\" name=\"upload\" value=\"Enviar\">"
            echo "          </form>"
            echo "      </p>"
        fi

    fi

    return 0

}

function end() {

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

trap "end 1" SIGQUIT SIGINT SIGHUP
mkdir $tmp_dir

### Cabeçalho
web_header

# Inicializar variáveis e constantes

if [ "$REQUEST_METHOD" == "POST" ]; then
    if [ "$CONTENT_TYPE" == "application/x-www-form-urlencoded" ]; then
        test -n "$CONTENT_LENGTH" && read -n "$CONTENT_LENGTH" POST_STRING

    elif echo "$CONTENT_TYPE" | grep -Ex "multipart/form-data; +boundary=.*" > /dev/null; then
        cat > "$tmp_dir/POST_CONTENT"
        parse_multipart_form "$tmp_dir/POST_CONTENT"

    fi
fi

#DEBUG
echo "<p>"
echo "  CONTENT_TYPE: <br>"
echo "$CONTENT_TYPE"
echo "</p>"
echo "<p>"
echo "  CONTENT_LENGTH: <br>"
echo "$CONTENT_LENGTH"
echo "</p>"
echo "<p>"
echo "  POST_STRING: <br>"
echo "$POST_STRING"
echo "</p>"
#DEBUG

mklist "$ambientes" "$tmp_dir/lista_ambientes"
proceed_view="Continuar"
proceed_deploy="Deploy"

if [ "$(cat $tmp_dir/POST_CONTENT | wc -l)" -eq 0 ]; then

    # Formulário deploy
    echo "      <p>"
    echo "          <form action=\"$start_page\" method=\"post\" enctype=\"multipart/form-data\">"
    # Sistema...
    echo "              <p>"
    echo "      		    <select class=\"select_default\" name=\"app\">"
    echo "		        	<option value=\"\" selected>Sistema...</option>"
    find $upload_dir/ -mindepth $((qtd_dir+1)) -maxdepth $((qtd_dir+1)) -type d | sort | uniq | xargs -I{} -d '\n' basename {} | sed -r "s|(.*)|\t\t\t\t\t<option>\1</option>|" 2> /dev/null
    echo "		            </select>"
    echo "              </p>"
    # Ambiente...
    echo "              <p>"
    echo "      		<select class=\"select_default\" name=\"env\">"
    echo "		        	<option value=\"\" selected>Ambiente...</option>"
    cat $tmp_dir/lista_ambientes | sort | sed -r "s|(.*)|\t\t\t\t\t<option>\1</option>|"
    echo "		        </select>"
    echo "              </p>"
    # Pacote (teste)
    echo "              <p>"
    echo "              Arquivo: <input type=\"file\" name=\"pkg\">"
    echo "              </p>"
    # Submit
    echo "              <p>"
    echo "              <input type=\"submit\" name=\"proceed\" value=\"$proceed_view\">"
    echo "              </p>"
    echo "          </form>"
    echo "      </p>"

else

    #DEBUG
    echo "<p>"
    echo "  FILE_NAME: <br>"
    echo "$pkg"
    echo "</p>"
    echo "<p>"
    echo "  FILE_MD5: <br>"
    md5sum $pkg
    echo "</p>"
    echo "<p>"
    echo "  APLICACAO: <br>"
    echo "$app"
    echo "</p>"
    echo "<p>"
    echo "  AMBIENTE: <br>"
    echo "$env"
    echo "</p>"
    #DEBUG

    # Processar POST_STRING
    #arg_string="&$(web_filter "$POST_STRING")&"
    #app_name=$(echo "$arg_string" | sed -rn "s/^.*&$app_param=([^\&]+)&.*$/\1/p")
    #env_name=$(echo "$arg_string" | sed -rn "s/^.*&$env_param=([^\&]+)&.*$/\1/p")
    #proceed=$(echo "$arg_string" | sed -rn "s/^.*&proceed=([^\&]+)&.*$/\1/p")

    if [ -n "$app_name" ] && [ -n "$env_name" ] && [ -n "$proceed" ]; then

        if [ "$proceed" == "$proceed_view" ]; then

            ### Visualizar parâmetros de deploy
            echo "      <p>"
            echo "          <table>"
            echo "              <tr><td>Sistema: </td><td>$app_name</td></tr>"
            echo "              <tr><td>Ambiente: </td><td>$env_name</td></tr>"
            echo "          </table>"
            echo "      </p>"

            submit_deploy

        else

            test -n "$REMOTE_USER" && user_name="$REMOTE_USER" || user_name="$(id --user --name)"
            # Realizar deploy

        fi
    else
        echo "      <p><b>Erro. Os parâmetro 'Sistema' e 'Ambiente' devem ser preenchidos.</b></p>"
    fi
fi

end 0
