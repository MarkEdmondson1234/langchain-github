# Code
def prime_sum():
    prime_numbers = [2]
    number = 3
    while len(prime_numbers) < 100:
        for p in prime_numbers:
            if number % p == 0:
                break
        else:
            prime_numbers.append(number)
        number += 2
    return sum(prime_numbers)