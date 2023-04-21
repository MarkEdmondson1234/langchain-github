# prime_numbers.py
def sum_of_first_100_prime_numbers():
    prime_nums = [2, 3]
    num = 3
    while len(prime_nums) < 100:
        num += 2
        for i in range(2, num):
            if num % i == 0:
                break
        else:
            prime_nums.append(num)
    return sum(prime_nums)