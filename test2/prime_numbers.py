def prime_sum(N): 
    prime_numbers = [2]
    x = 3
    while len(prime_numbers) < N:
        for y in range(3,x,2):  # test all odd factors up to x-1
            if x%y == 0:
                x += 2
                break
        else:
            prime_numbers.append(x)
            x += 2
    return sum(prime_numbers)