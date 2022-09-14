import uuid
from typing import Union, List, Optional
from dataclasses import dataclass, field, is_dataclass
from datamodel.base import BaseModel, Column, Field

def auto_uid():
    return uuid.uuid4()

class User(BaseModel):
    name: str
    first_name: str
    last_name: str

@dataclass
class Address:
    street: str
    city: str
    state: str
    zipcode: str
    country: Optional[str] = 'US'

    def __str__(self) -> str:
        """Provides pretty response of address"""
        lines = [self.street]
        lines.append(f"{self.city}, {self.zipcode} {self.state}")
        lines.append(f"{self.country}")
        return "\n".join(lines)

class Employee(User):
    """
    Base Employee.
    """
    id: uuid.UUID = field(default_factory=auto_uid)
    role: str
    address: Address # composition of a dataclass inside of DataModel

    def info(self) -> str:
        return f"Name is {self.first_name}, {self.last_name}"

# Supporting multiple inheritance, even from pure dataclasses
# Wage Policies
class MonthlySalary(BaseModel):
    salary: Union[float, int]

    def calculate_payroll(self) -> Union[float, int]:
        return self.salary

class HourlySalary(BaseModel):
    salary: Union[float, int] = Field(default=0)
    hours_worked: Union[float, int] = Field(default=0)

    def calculate_payroll(self) -> Union[float, int]:
        return (self.hours_worked * self.salary)

class CommissionPolicy(BaseModel):
    commission: Union[int, float] = Column(default=0)

    def calculate_payroll(self) -> Union[float, int]:
        # adding the commission to the base payroll
        fixed = super().calculate_payroll()
        return fixed + self.commission

# TYpes of Employees
class Manager(Employee, MonthlySalary, CommissionPolicy):
    """
    Manager is an employee montly salary policy and commissions.
    """
    role: str = 'Manager'

class SalesPerson(Employee, HourlySalary, CommissionPolicy):
    """
    SalesPerson is an employee with hourly salary policy and commissions.
    """
    role: str = 'Sales Person'

class Secretary(Employee, MonthlySalary):
    """Secretary.

    Person with montly salary policy and no commissions.
    """
    role: str = 'Secretary'

class FactoryWorker(Employee, HourlySalary):
    """
    FactoryWorker is an employee with hourly salary policy and no commissions.
    """
    role: str = 'Factory Worker'

class PayrollSystem:
    def calculate_payroll(self, employees: List[dataclass]) -> None:
        print('=== Calculating Payroll === ')
        for employee in employees:
            print(f"Payroll for employee {employee.id} - {employee.name}")
            print(f"- {employee.role} Amount: {employee.calculate_payroll()}")
            if employee.address:
                print('- Sent to:')
                print(employee.address)
            print("")


# Testing Model:
john = Manager(name='John Doe', first_name='John', last_name='Doe', salary=2500, commission=500)
john.address = Address('121 Admin Road', "Concord", "NH", "03301")
jane = Secretary(name='Jane Doe', first_name='Jane', last_name='Doe', salary=1500)
jane.address = Address('Rodeo Drive, Rd', 'Los Angeles', 'CA', '31050')
bob = FactoryWorker(name='Bob Doyle', first_name='Bob', last_name='Doyle', salary=15, hours_worked=40)
mitch = FactoryWorker(name='Mitch Brian', first_name='Mitch', last_name='Brian', salary=20, hours_worked=35)
kevin = SalesPerson(name='Kevin Bacon', first_name='Kevin', last_name='Bacon', salary=35, hours_worked=35, commission=250)

payroll = PayrollSystem()
payroll.calculate_payroll([jane, bob, mitch, john, kevin])

print('IS DATACLASS? > ', is_dataclass(mitch))
