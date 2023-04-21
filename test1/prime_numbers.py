def prime_sum():
    prime_list = []
    for num in range(2, 1000):
        if all(num % i != 0 for i in range(2, num)):
            prime_list.append(num)
    return sum(prime_list[:100])