from selenium.webdriver.common.by import By

from conftest import BASE_URL


# ---------- helpers ----------
def login(driver, username="demo", password="demo123"):
    driver.get(f"{BASE_URL}/login")
    driver.find_element(By.ID, "username").send_keys(username)
    driver.find_element(By.ID, "password").send_keys(password)
    driver.find_element(By.ID, "login-btn").click()


def balance(driver):
    return driver.find_element(By.ID, "balance").text


def flash(driver):
    return driver.find_element(By.ID, "flash").text


def do(driver, kind, amount):
    driver.find_element(By.ID, f"{kind}-amount").send_keys(amount)
    driver.find_element(By.ID, f"{kind}-btn").click()


# ---------- tests ----------
def test_login_success(driver):
    login(driver)
    assert "/dashboard" in driver.current_url
    assert driver.find_element(By.ID, "welcome-user").text == "demo"
    assert balance(driver) == "$1,000.00"


def test_login_invalid_password(driver):
    login(driver, password="wrong")
    assert "/login" in driver.current_url
    assert "Invalid username or password" in flash(driver)


def test_dashboard_requires_login(driver):
    driver.get(f"{BASE_URL}/dashboard")
    assert "/login" in driver.current_url


def test_deposit(driver):
    login(driver)
    do(driver, "deposit", "250.50")
    assert "Deposit of $250.50 successful" in flash(driver)
    assert balance(driver) == "$1,250.50"


def test_withdraw(driver):
    login(driver)
    do(driver, "withdraw", "400")
    assert "Withdraw of $400.00 successful" in flash(driver)
    assert balance(driver) == "$600.00"


def test_withdraw_more_than_balance(driver):
    login(driver)
    do(driver, "withdraw", "5000")
    assert "Insufficient funds" in flash(driver)
    assert balance(driver) == "$1,000.00"


def test_negative_withdraw_rejected(driver):
    login(driver)
    do(driver, "withdraw", "-50")
    assert "greater than zero" in flash(driver)
    assert balance(driver) == "$1,000.00"


def test_non_numeric_deposit_rejected(driver):
    login(driver)
    do(driver, "deposit", "abc")
    assert "valid number" in flash(driver)
    assert balance(driver) == "$1,000.00"


def test_transaction_history(driver):
    login(driver)
    do(driver, "deposit", "100")
    do(driver, "withdraw", "30")
    driver.find_element(By.ID, "nav-history").click()

    rows = driver.find_elements(By.CSS_SELECTOR, "#txn-table .txn-row")
    assert len(rows) == 2
    # newest first
    assert rows[0].find_element(By.CLASS_NAME, "txn-type").text == "withdraw"
    assert rows[0].find_element(By.CLASS_NAME, "txn-amount").text == "$30.00"
    assert rows[1].find_element(By.CLASS_NAME, "txn-type").text == "deposit"
    assert rows[1].find_element(By.CLASS_NAME, "txn-amount").text == "$100.00"


def test_history_empty_for_new_session(driver):
    login(driver)
    driver.find_element(By.ID, "nav-history").click()
    assert driver.find_element(By.ID, "no-txns").is_displayed()


def test_logout(driver):
    login(driver)
    driver.find_element(By.ID, "nav-logout").click()
    assert "/login" in driver.current_url
    driver.get(f"{BASE_URL}/dashboard")
    assert "/login" in driver.current_url
