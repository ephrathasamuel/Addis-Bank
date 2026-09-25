# bank.py
# Addis Bank — Account Management System

from datetime import datetime
from abc import ABC, abstractmethod


class BankConfig:
    _instance = None

    def __new__(cls):
        if cls._instance is None:
            cls._instance = super().__new__(cls)
            cls._instance.interest_rate = 0.05
            cls._instance.overdraft_limit = 1000
        return cls._instance


class Account:

    def __init__(self, owner, number, balance=0):
        self.owner = owner
        self.account_number = number
        self.__balance = balance
        self._observers = []
        self.history = []

    @property
    def balance(self):
        return self.__balance

    def subscribe(self, observer):
        self._observers.append(observer)

    def unsubscribe(self, observer):
        self._observers.remove(observer)

    def _notify(self, event):
        for observer in self._observers:
            observer.update(event)

    def deposit(self, amount, record=True):
        if amount <= 0:
            raise ValueError("Amount must be positive")
        self.__balance += amount
        if record:
            self.history.append(("deposit", amount))
        self._notify(f"{self.owner} deposited {amount:.2f} ETB "
                      f"(balance: {self.__balance:.2f} ETB)")

    def withdraw(self, amount, record=True):
        if amount <= 0:
            raise ValueError("Amount must be positive")
        if amount > self.__balance:
            raise ValueError("Insufficient funds — cannot overdraw account")
        self.__balance -= amount
        if record:
            self.history.append(("withdraw", amount))
        self._notify(f"{self.owner} withdrew {amount:.2f} ETB "
                      f"(balance: {self.__balance:.2f} ETB)")

    def _apply_delta(self, delta):
        self.__balance += delta

    def statement(self):
        print(f"[Account] Owner: {self.owner} | "
              f"No: {self.account_number} | "
              f"Balance: {self.balance:.2f} ETB")


class SavingsAccount(Account):
    def __init__(self, owner, number, balance=0, rate=None):
        super().__init__(owner, number, balance)
        self.rate = rate if rate is not None else BankConfig().interest_rate

    def add_interest(self):
        interest = self.balance * self.rate
        self.deposit(interest)
        return interest

    def statement(self):
        print(f"[Savings] Owner: {self.owner} | "
              f"No: {self.account_number} | "
              f"Balance: {self.balance:.2f} ETB | "
              f"Rate: {self.rate * 100:.1f}%")


class CurrentAccount(Account):
    def __init__(self, owner, number, balance=0, overdraft_limit=None):
        super().__init__(owner, number, balance)
        self.overdraft_limit = (
            overdraft_limit if overdraft_limit is not None
            else BankConfig().overdraft_limit
        )

    def withdraw(self, amount, record=True):
        if amount <= 0:
            raise ValueError("Amount must be positive")
        if amount > self.balance + self.overdraft_limit:
            raise ValueError("Insufficient funds — exceeds overdraft limit")
        self._apply_delta(-amount)
        if record:
            self.history.append(("withdraw", amount))
        self._notify(f"{self.owner} withdrew {amount:.2f} ETB "
                      f"(balance: {self.balance:.2f} ETB)")

    def statement(self):
        print(f"[Current] Owner: {self.owner} | "
              f"No: {self.account_number} | "
              f"Balance: {self.balance:.2f} ETB | "
              f"Overdraft limit: {self.overdraft_limit:.2f} ETB")


class AccountFactory:
    @staticmethod
    def create(kind, owner, number, balance=0):
        kind = kind.lower()
        if kind == "savings":
            return SavingsAccount(owner, number, balance)
        if kind == "current":
            return CurrentAccount(owner, number, balance)
        if kind == "account":
            return Account(owner, number, balance)
        raise ValueError(f"Unknown account type: {kind}")


class Notifier(ABC):
    @abstractmethod
    def update(self, event):
        pass


class SMSAlert(Notifier):
    def update(self, event):
        print(f"[TeleBirr SMS] {event}")


class AuditLog(Notifier):
    def update(self, event):
        print(f"[Log] {event}")


def binary_search(sorted_items, target):
    low, high = 0, len(sorted_items) - 1
    while low <= high:
        mid = (low + high) // 2
        if sorted_items[mid] == target:
            return mid
        elif sorted_items[mid] < target:
            low = mid + 1
        else:
            high = mid - 1
    return -1


class AccountRegistry:
    def __init__(self):
        self.by_number = {}
        self.order = []

    def add(self, acc):
        self.by_number[acc.account_number] = acc
        self.order.append(acc.account_number)

    def find(self, number):
        return self.by_number.get(number)

    def list_all(self):
        return [self.by_number[num] for num in self.order]

    def top_by_balance(self, n=5):
        accts = sorted(
            self.by_number.values(),
            key=lambda a: a.balance,
            reverse=True,
        )
        return accts[:n]

    def find_by_number(self, number):
        nums = sorted(self.by_number)
        i = binary_search(nums, number)
        return self.by_number[nums[i]] if i >= 0 else None

    def total_transactions(self, number):
        acc = self.find(number)
        if acc is None:
            raise ValueError(f"No account with number {number}")
        return self._sum_history(acc.history)

    def _sum_history(self, history):
        if not history:
            return 0
        action, amount = history[0]
        signed_amount = amount if action == "deposit" else -amount
        return signed_amount + self._sum_history(history[1:])

    def undo_last(self, number):
        acc = self.find(number)
        if acc is None:
            raise ValueError(f"No account with number {number}")
        if not acc.history:
            print(f"No transactions to undo for {number}")
            return None

        action, amount = acc.history.pop()
        if action == "deposit":
            acc.withdraw(amount, record=False)
            print(f"Undid deposit of {amount:.2f} ETB on {number}")
        elif action == "withdraw":
            acc.deposit(amount, record=False)
            print(f"Undid withdrawal of {amount:.2f} ETB on {number}")
        return action, amount


class Branch:
    def __init__(self, name):
        self.name = name
        self.children = []
        self.accounts = []

    def add_child(self, branch):
        self.children.append(branch)

    def add_account(self, account):
        self.accounts.append(account)

    def total_balance(self):
        total = sum(a.balance for a in self.accounts)
        for child in self.children:
            total += child.total_balance()
        return total

    def print_tree(self, depth=0):
        indent = "  " * depth
        print(f"{indent}{self.name} "
              f"(direct accounts: {len(self.accounts)}, "
              f"subtotal: {self.total_balance():.2f} ETB)")
        for child in self.children:
            child.print_tree(depth + 1)


def bfs(transfers, start):
    visited = {start}
    queue = [start]

    while queue:
        current = queue.pop(0)
        for recipient in transfers.get(current, []):
            if recipient not in visited:
                visited.add(recipient)
                queue.append(recipient)

    return visited


class AddisBank:
    def __init__(self):
        self.registry = AccountRegistry()
        self.transactions = []
        self.config = BankConfig()
        self.current_account = 10000
        self.head_office = Branch("Head Office")

    def show_menu(self):
        print("\n wellcome to Addis Bank"
        "\n1 Create  \n 2 View all accounts \n 3 find account \n 4 top account \n 5 Deposit  "
              "\n 6 Withdraw  \n 7 check balance  \n 8 transfer  \n 9 view transactions  "
              "\n 10 Add Interest \n 11 view statistics \n 12 branch tree over view \n 13 undo transaction \n 0 exit")

    def getinput(self, prompt, input_type):
        while True:
            choice = input(prompt)
            try:
                return input_type(choice)
            except ValueError:
                print("please choose from the given options")

    def run(self):
        while True:
            self.show_menu()
            choice = self.getinput('Please Enter Your Choice: ', int)
            if choice == 1:
                self.create_new_account()
            elif choice == 2:
                self.view_all_accounts()
            elif choice == 3:
                self.find_account()
            elif choice == 4:
                self.top_accounts()
            elif choice == 5:
                self.deposit_money()
            elif choice == 6:
                self.withdraw_money()
            elif choice == 7:
                self.check_balance()
            elif choice == 8:
                self.transfer_money()
            elif choice == 9:
                self.view_transactions()
            elif choice == 10:
                self.add_interest()
            elif choice == 11:
                self.view_statistics()
            elif choice == 12:
                self.branch_tree_overview()
            elif choice == 13:
                self.undo_transaction()
            elif choice == 0:
                print("Thank you for banking with Addis Bank. Goodbye!")
                break
            else:
                print("Error, Please enter A Valid Choice")

    def create_new_account(self):
        try:
            print("\n1 Basic, \n 2 Saving, \n 3 current")
            choice = self.getinput("choose from the following", int)
            name = self.getinput("Please inser Your FULL Name Here", str)
            self.current_account += 1
            account_number = f'CBE {self.current_account}'
            initial_amount = self.getinput("How Much Would You Like To Deposit?", int)

            if choice == 1:
                acc = AccountFactory.create("account", name, account_number, initial_amount)
            elif choice == 2:
                acc = AccountFactory.create("savings", name, account_number, initial_amount)
            elif choice == 3:
                acc = AccountFactory.create("current", name, account_number, initial_amount)
            else:
                print("Error, Please enter A Valid Choice")
                return

            acc.subscribe(SMSAlert())
            acc.subscribe(AuditLog())
            self.registry.add(acc)
            self.head_office.add_account(acc)
            print("Account Created!")
            print(account_number)
        except ValueError as e:
            print(e)

    def view_all_accounts(self):
        accounts = self.registry.list_all()
        if not accounts:
            print("No accounts yet.")
            return
        for acc in accounts:
            acc.statement()

    def find_account(self):
        number = self.getinput("Account number: ", str)
        acc = self.registry.find(number)
        if acc is None:
            print(f"No account found with number {number}.")
            return
        acc.statement()

    def top_accounts(self):
        n = self.getinput("How many top accounts to show: ", int)
        leaders = self.registry.top_by_balance(n)
        if not leaders:
            print("No accounts yet.")
            return
        for acc in leaders:
            print(f"{acc.account_number} ({acc.owner}): {acc.balance:.2f} ETB")

    def deposit_money(self):
        number = self.getinput("Account number: ", str)
        acc = self.registry.find(number)
        if acc is None:
            print(f"No account found with number {number}.")
            return
        amount = self.getinput("Deposit amount: ", float)
        try:
            acc.deposit(amount)
        except ValueError as e:
            print(e)
            return
        self._log(number, "deposit", amount, acc.balance)
        print(f"Deposited {amount:.2f} ETB. New balance: {acc.balance:.2f} ETB.")

    def withdraw_money(self):
        number = self.getinput("Account number: ", str)
        acc = self.registry.find(number)
        if acc is None:
            print(f"No account found with number {number}.")
            return
        amount = self.getinput("Withdraw amount: ", float)
        try:
            acc.withdraw(amount)
        except ValueError as e:
            print(e)
            return
        self._log(number, "withdraw", amount, acc.balance)
        print(f"Withdrew {amount:.2f} ETB. New balance: {acc.balance:.2f} ETB.")

    def check_balance(self):
        number = self.getinput("Account number: ", str)
        acc = self.registry.find(number)
        if acc is None:
            print(f"No account found with number {number}.")
            return
        print(f"Balance for {number}: {acc.balance:.2f} ETB")

    def transfer_money(self):
        from_number = self.getinput("From account number: ", str)
        to_number = self.getinput("To account number: ", str)
        from_acc = self.registry.find(from_number)
        to_acc = self.registry.find(to_number)
        if from_acc is None or to_acc is None:
            print("Both accounts must exist to transfer.")
            return
        amount = self.getinput("Transfer amount: ", float)
        try:
            from_acc.withdraw(amount)
        except ValueError as e:
            print(e)
            return
        to_acc.deposit(amount)
        self._log(from_number, "transfer_out", amount, from_acc.balance)
        self._log(to_number, "transfer_in", amount, to_acc.balance)
        print(f"Transferred {amount:.2f} ETB from {from_number} to {to_number}.")

    def view_transactions(self):
        number = self.getinput("Account number: ", str)
        rows = [t for t in self.transactions if t["account"] == number]
        if not rows:
            print(f"No transactions recorded for {number}.")
            return
        for t in rows:
            print(f"{t['time']} | {t['type']:<12} | {t['amount']:.2f} ETB | "
                  f"balance after: {t['balance_after']:.2f} ETB")

    def add_interest(self):
        number = self.getinput("Account number: ", str)
        acc = self.registry.find(number)
        if acc is None:
            print(f"No account found with number {number}.")
            return
        if not isinstance(acc, SavingsAccount):
            print(f"{number} is not a savings account — interest doesn't apply.")
            return
        interest = acc.add_interest()
        self._log(number, "interest", interest, acc.balance)
        print(f"Added {interest:.2f} ETB interest. New balance: {acc.balance:.2f} ETB.")

    def view_statistics(self):
        accounts = self.registry.list_all()
        if not accounts:
            print("No accounts yet.")
            return
        total = sum(a.balance for a in accounts)
        print(f"Total accounts: {len(accounts)}")
        print(f"Total balance: {total:.2f} ETB")
        print(f"Average balance: {total / len(accounts):.2f} ETB")

    def branch_tree_overview(self):
        self.head_office.print_tree()

    def undo_transaction(self):
        number = self.getinput("Account number: ", str)
        try:
            self.registry.undo_last(number)
        except ValueError as e:
            print(e)

    def _log(self, number, kind, amount, balance_after):
        self.transactions.append({
            "time": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
            "account": number,
            "type": kind,
            "amount": amount,
            "balance_after": balance_after,
        })


if __name__ == "__main__":
    AddisBank().run()