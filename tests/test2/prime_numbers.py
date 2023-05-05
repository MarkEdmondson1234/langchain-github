def prime_sum(n):
    prime_numbers = []
    current_number = 2
    while len(prime_numbers) < n:
        is_prime = True
        for prime in prime_numbers:
            if current_number % prime == 0:
                is_prime = False
                break
        if is_prime:
            prime_numbers.append(current_number)
        current_number += 1
    return sum(prime_numbers)