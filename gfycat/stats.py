import json
from words import adjectives, animals

"""
quick and dirty script to reduce the original 
words length to have a public address name that
is at maximum X character long 
"""

def main():
    adj, anm = reduce(adjectives, animals)
    with open('animals.json','w') as fp:
        json.dump(anm, fp, indent=2)
    with open('adjectives.json', 'w') as fp:
        json.dump(adj, fp, indent=2)


def reduce(adjectives, animals, lim=33):

    m1, w1, i1 = 0, '', -1
    for i, a in enumerate(adjectives):
        if len(a) > m1:
            m1, w1, i1 = len(a), a, i

    print(f'max adj: {m1} - {w1} at {i1}')

    m2, w2, i2 = 0, '', -1
    for i, a in enumerate(animals):
        if len(a) > m2:
            m2, w2, i2 = len(a), a, i

    print(f'max anm: {m2} - {w2} at {i2}')

    adj_l = len(adjectives)
    anm_l = len(animals)

    perms = adj_l * (adj_l - 1) + anm_l
    length = m1 * 2 + m2 + 2
    print(f'total length max {length}, permutation {perms}')

    if length > lim:
        print(f'length {length} greather than {lim}, reducing')
        # remove the longest word
        if len(w2) > len(w1):
            print(f'remove {w2} from animals since is longer than {w1}')
            animals.pop(i2)
        else:
            print(f'remove {w1} from adj')
            adjectives.pop(i1)
        return reduce(adjectives, animals, lim=lim)
    return adjectives, animals


if __name__ == '__main__':
    main()
