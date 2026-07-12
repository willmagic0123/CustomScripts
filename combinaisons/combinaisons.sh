#!/bin/bash
start_time=$(date +%s%N)
count=0

for a in a b c d e f g h i j k l m n o p q r s t u v w x y z A B C D E F G H I J K L M N O P Q R S T U V W X Y Z 0 1 2 3 4 5 6 7 8 9 "!" "@" "#" "$" "%" "?" "*" "(" ")" "_" "+" "-" "=" "[" "]" "{" "}"
do
    for b in a b c d e f g h i j k l m n o p q r s t u v w x y z A B C D E F G H I J K L M N O P Q R S T U V W X Y Z 0 1 2 3 4 5 6 7 8 9 "!" "@" "#" "$" "%" "?" "*" "(" ")" "_" "+" "-" "=" "[" "]" "{" "}"
    do
        for c in a b c d e f g h i j k l m n o p q r s t u v w x y z A B C D E F G H I J K L M N O P Q R S T U V W X Y Z 0 1 2 3 4 5 6 7 8 9 "!" "@" "#" "$" "%" "?" "*" "(" ")" "_" "+" "-" "=" "[" "]" "{" "}"
        do
            for d in a b c d e f g h i j k l m n o p q r s t u v w x y z A B C D E F G H I J K L M N O P Q R S T U V W X Y Z 0 1 2 3 4 5 6 7 8 9 "!" "@" "#" "$" "%" "?" "*" "(" ")" "_" "+" "-" "=" "[" "]" "{" "}"
            do
                echo "$a$b$c$d"
                ((count++))
            done
        done
    done
done

end_time=$(date +%s%N)
elapsed_ns=$((end_time - start_time))
elapsed_ms=$((elapsed_ns / 1000000))
seconds=$((elapsed_ms / 1000))
milliseconds=$((elapsed_ms % 1000))
echo "BASH - Combinaisons: $count - Temps: ${seconds}s ${milliseconds}ms"
