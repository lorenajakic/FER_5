def save_results_to_file(results, filename):
    with open(filename, 'w') as file:
        print(f"Saving results to {filename}...")
        file.write("t,x1,x2\n")
        for result in results:
            t = result[0]
            x_values = result[1:]
            file.write(f"{t},{",".join(map(str, x_values))}\n")
