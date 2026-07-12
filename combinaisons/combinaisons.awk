BEGIN {
    split("a b c d e f g h i j k l m n o p q r s t u v w x y z A B C D E F G H I J K L M N O P Q R S T U V W X Y Z 0 1 2 3 4 5 6 7 8 9 ! @ # $ % ? * ( ) _ + - = [ ] { }", chars, " ")
    n = length(chars)

    "date +%s%N" | getline start_ns
    close("date +%s%N")

    count = 0
    for (i = 1; i <= n; i++) {
        a = chars[i]
        for (j = 1; j <= n; j++) {
            b = chars[j]
            for (k = 1; k <= n; k++) {
                c = chars[k]
                for (l = 1; l <= n; l++) {
                    d = chars[l]
                    s = a b c d
                    count++
                }
            }
        }
    }

    "date +%s%N" | getline end_ns
    close("date +%s%N")

    elapsed_ns = end_ns - start_ns
    elapsed_ms = int(elapsed_ns / 1000000)
    seconds = int(elapsed_ms / 1000)
    milliseconds = elapsed_ms % 1000
    printf "AWK - Combinaisons: %d - Temps: %ds %dms\n", count, seconds, milliseconds
}
