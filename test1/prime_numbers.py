def prime_sum():
    prime_numbers = [2]
    num = 3
    while len(prime_numbers) < 100:
        for p in prime_numbers:
            if num % p == 0:
                break
        else:
            prime_numbers.append(num)
        num += 2
    return sum(prime_numbers)