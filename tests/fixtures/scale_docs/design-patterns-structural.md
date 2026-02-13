---
title: Structural Design Patterns
description: Detailed technical documentation on Structural Design Patterns including Adapter, Bridge, Composite, Decorator, Facade, Flyweight, and Proxy with code examples.
keywords: 
  - design patterns
  - structural patterns
  - adapter
  - bridge
  - composite
  - decorator
  - facade
  - flyweight
  - proxy
category: software-architecture
tags:
  - design-patterns
  - software-architecture
  - object-oriented-programming
---

## Structural Design Patterns

Structural design patterns are a category of software design patterns that concern the composition of classes and objects. These patterns focus on how objects are connected to each other and how they can be organized into larger structures.

The structural design patterns covered in this document are:

1. Adapter
2. Bridge
3. Composite
4. Decorator
5. Facade
6. Flyweight
7. Proxy

### Adapter

The Adapter pattern is used to provide a linking interface between two otherwise incompatible interfaces. It acts as a bridge, converting the interface of a class into another interface the client expects. This allows classes to work together that couldn't otherwise because of incompatible interfaces.

#### Example - Java

Imagine you have an existing `LegacyRoundPeg` class that has a `getDiameter()` method, but you need to use it with a `SquarePeg` interface that expects a `getWidth()` and `getHeight()` method. You can create an adapter to bridge the gap:

```java
// The adaptee
public class LegacyRoundPeg {
    private double diameter;

    public LegacyRoundPeg(double diameter) {
        this.diameter = diameter;
    }

    public double getDiameter() {
        return diameter;
    }
}

// The target interface
public interface SquarePeg {
    double getWidth();
    double getHeight();
}

// The adapter
public class SquarePegAdapter implements SquarePeg {
    private LegacyRoundPeg roundPeg;

    public SquarePegAdapter(LegacyRoundPeg roundPeg) {
        this.roundPeg = roundPeg;
    }

    @Override
    public double getWidth() {
        return roundPeg.getDiameter();
    }

    @Override
    public double getHeight() {
        return roundPeg.getDiameter();
    }
}

// Usage
LegacyRoundPeg roundPeg = new LegacyRoundPeg(5.0);
SquarePeg squarePeg = new SquarePegAdapter(roundPeg);
```

In this example, the `SquarePegAdapter` class acts as a bridge between the `LegacyRoundPeg` and the `SquarePeg` interface, allowing them to work together.

#### Example - Python

Here's an example of the Adapter pattern in Python:

```python
# The adaptee
class LegacyRoundPeg:
    def __init__(self, diameter):
        self.diameter = diameter

    def get_diameter(self):
        return self.diameter

# The target interface
class SquarePeg:
    def get_width(self):
        pass

    def get_height(self):
        pass

# The adapter
class SquarePegAdapter(SquarePeg):
    def __init__(self, round_peg):
        self.round_peg = round_peg

    def get_width(self):
        return self.round_peg.get_diameter()

    def get_height(self):
        return self.round_peg.get_diameter()

# Usage
round_peg = LegacyRoundPeg(5.0)
square_peg = SquarePegAdapter(round_peg)
```

In this example, the `SquarePegAdapter` class acts as a bridge between the `LegacyRoundPeg` and the `SquarePeg` interface, allowing them to work together.

### Bridge

The Bridge pattern is used to decouple an abstraction from its implementation, so that the two can vary independently. It provides a way to split a large class or a set of closely related classes into two separate hierarchies - abstraction and implementation - which can be developed independently of each other.

#### Example - Java

Imagine you have a `Vehicle` class hierarchy with different types of vehicles, and each vehicle has a specific `Engine` implementation. Using the Bridge pattern, you can decouple the `Vehicle` abstraction from the `Engine` implementation:

```java
// Implementor
public interface Engine {
    void start();
    void stop();
}

// Concrete Implementor
public class PetrolEngine implements Engine {
    @Override
    public void start() {
        System.out.println("Starting petrol engine...");
    }

    @Override
    public void stop() {
        System.out.println("Stopping petrol engine...");
    }
}

// Concrete Implementor
public class ElectricEngine implements Engine {
    @Override
    public void start() {
        System.out.println("Starting electric engine...");
    }

    @Override
    public void stop() {
        System.out.println("Stopping electric engine...");
    }
}

// Abstraction
public abstract class Vehicle {
    protected Engine engine;

    public Vehicle(Engine engine) {
        this.engine = engine;
    }

    public void startVehicle() {
        engine.start();
    }

    public void stopVehicle() {
        engine.stop();
    }
}

// Refined Abstraction
public class Car extends Vehicle {
    public Car(Engine engine) {
        super(engine);
    }

    public void drive() {
        System.out.println("Driving a car...");
    }
}

// Refined Abstraction
public class Motorcycle extends Vehicle {
    public Motorcycle(Engine engine) {
        super(engine);
    }

    public void ride() {
        System.out.println("Riding a motorcycle...");
    }
}

// Usage
Engine petrolEngine = new PetrolEngine();
Car car = new Car(petrolEngine);
car.startVehicle(); // Starting petrol engine...
car.drive(); // Driving a car...
car.stopVehicle(); // Stopping petrol engine...

Engine electricEngine = new ElectricEngine();
Motorcycle motorcycle = new Motorcycle(electricEngine);
motorcycle.startVehicle(); // Starting electric engine...
motorcycle.ride(); // Riding a motorcycle...
motorcycle.stopVehicle(); // Stopping electric engine...
```

In this example, the `Vehicle` abstraction is decoupled from the `Engine` implementation, allowing them to vary independently. The `Car` and `Motorcycle` classes are refined abstractions that can use different `Engine` implementations.

#### Example - Python

Here's an example of the Bridge pattern in Python:

```python
# Implementor
class Engine:
    def start(self):
        pass

    def stop(self):
        pass

# Concrete Implementor
class PetrolEngine(Engine):
    def start(self):
        print("Starting petrol engine...")

    def stop(self):
        print("Stopping petrol engine...")

# Concrete Implementor
class ElectricEngine(Engine):
    def start(self):
        print("Starting electric engine...")

    def stop(self):
        print("Stopping electric engine...")

# Abstraction
class Vehicle:
    def __init__(self, engine):
        self.engine = engine

    def start_vehicle(self):
        self.engine.start()

    def stop_vehicle(self):
        self.engine.stop()

# Refined Abstraction
class Car(Vehicle):
    def drive(self):
        print("Driving a car...")

# Refined Abstraction
class Motorcycle(Vehicle):
    def ride(self):
        print("Riding a motorcycle...")

# Usage
petrol_engine = PetrolEngine()
car = Car(petrol_engine)
car.start_vehicle()  # Starting petrol engine...
car.drive()  # Driving a car...
car.stop_vehicle()  # Stopping petrol engine...

electric_engine = ElectricEngine()
motorcycle = Motorcycle(electric_engine)
motorcycle.start_vehicle()  # Starting electric engine...
motorcycle.ride()  # Riding a motorcycle...
motorcycle.stop_vehicle()  # Stopping electric engine...
```

In this example, the `Vehicle` abstraction is decoupled from the `Engine` implementation, allowing them to vary independently. The `Car` and `Motorcycle` classes are refined abstractions that can use different `Engine` implementations.

### Composite

The Composite pattern is used to create hierarchical tree-like structures of objects, where each object in the tree can be treated the same way (as if they were individual objects). This pattern composes objects into tree structures to represent part-whole hierarchies, allowing clients to treat individual objects and compositions of objects uniformly.

#### Example - Java

Imagine you have a file system with directories and files. You can use the Composite pattern to represent this hierarchy:

```java
// Component
public interface FileSystemItem {
    void display();
}

// Leaf
public class File implements FileSystemItem {
    private String name;

    public File(String name) {
        this.name = name;
    }

    @Override
    public void display() {
        System.out.println("File: " + name);
    }
}

// Composite
public class Directory implements FileSystemItem {
    private String name;
    private List<FileSystemItem> contents = new ArrayList<>();

    public Directory(String name) {
        this.name = name;
    }

    public void add(FileSystemItem item) {
        contents.add(item);
    }

    public void remove(FileSystemItem item) {
        contents.remove(item);
    }

    @Override
    public void display() {
        System.out.println("Directory: " + name);
        for (FileSystemItem item : contents) {
            item.display();
        }
    }
}

// Usage
Directory root = new Directory("root");
File file1 = new File("file1.txt");
File file2 = new File("file2.txt");
Directory dir1 = new Directory("dir1");
File file3 = new File("file3.txt");

root.add(file1);
root.add(file2);
root.add(dir1);
dir1.add(file3);

root.display();
/*
Output:
Directory: root
File: file1.txt
File: file2.txt
Directory: dir1
File: file3.txt
*/
```

In this example, the `FileSystemItem` interface is the component, and `File` and `Directory` are the leaf and composite nodes, respectively. The `Directory` class can contain both files and other directories, allowing for the creation of a hierarchical file system structure.

#### Example - Python

Here's an example of the Composite pattern in Python:

```python
# Component
class FileSystemItem:
    def display(self):
        pass

# Leaf
class File(FileSystemItem):
    def __init__(self, name):
        self.name = name

    def display(self):
        print(f"File: {self.name}")

# Composite
class Directory(FileSystemItem):
    def __init__(self, name):
        self.name = name
        self.contents = []

    def add(self, item):
        self.contents.append(item)

    def remove(self, item):
        self.contents.remove(item)

    def display(self):
        print(f"Directory: {self.name}")
        for item in self.contents:
            item.display()

# Usage
root = Directory("root")
file1 = File("file1.txt")
file2 = File("file2.txt")
dir1 = Directory("dir1")
file3 = File("file3.txt")

root.add(file1)
root.add(file2)
root.add(dir1)
dir1.add(file3)

root.display()
"""
Output:
Directory: root
File: file1.txt
File: file2.txt
Directory: dir1
File: file3.txt
"""
```

In this example, the `FileSystemItem` class is the component, and `File` and `Directory` are the leaf and composite nodes, respectively. The `Directory` class can contain both files and other directories, allowing for the creation of a hierarchical file system structure.

### Decorator

The Decorator pattern is used to dynamically add new responsibilities to an object by wrapping it with another object. This provides a flexible alternative to subclassing for extending functionality.

#### Example - Java

Imagine you have a simple `Coffee` class, and you want to add additional decorations (milk, sugar, etc.) to it. You can use the Decorator pattern to achieve this:

```java
// Component
public interface Coffee {
    double getCost();
    String getDescription();
}

// Concrete Component
public class SimpleCoffee implements Coffee {
    @Override
    public double getCost() {
        return 1.0;
    }

    @Override
    public String getDescription() {
        return "Simple coffee";
    }
}

// Decorator
public abstract class CoffeeDecorator implements Coffee {
    protected Coffee decoratedCoffee;

    public CoffeeDecorator(Coffee coffee) {
        this.decoratedCoffee = coffee;
    }

    @Override
    public double getCost() {
        return decoratedCoffee.getCost();
    }

    @Override
    public String getDescription() {
        return decoratedCoffee.getDescription();
    }
}

// Concrete Decorator
public class MilkDecorator extends CoffeeDecorator {
    public MilkDecorator(Coffee coffee) {
        super(coffee);
    }

    @Override
    public double getCost() {
        return super.getCost() + 0.5;
    }

    @Override
    public String getDescription() {
        return super.getDescription() + ", milk";
    }
}

// Concrete Decorator
public class SugarDecorator extends CoffeeDecorator {
    public SugarDecorator(Coffee coffee) {
        super(coffee);
    }

    @Override
    public double getCost() {
        return super.getCost() + 0.2;
    }

    @Override
    public String getDescription() {
        return super.getDescription() + ", sugar";
    }
}

// Usage
Coffee simpleCoffee = new SimpleCoffee();
System.out.println(simpleCoffee.getDescription() + " costs $" + simpleCoffee.getCost());

Coffee coffeeWithMilk = new MilkDecorator(simpleCoffee);
System.out.println(coffeeWithMilk.getDescription() + " costs $" + coffeeWithMilk.getCost());

Coffee coffeeWithMilkAndSugar = new SugarDecorator(new MilkDecorator(simpleCoffee));
System.out.println(coffeeWithMilkAndSugar.getDescription() + " costs $" + coffeeWithMilkAndSugar.getCost());
```

In this example, the `Coffee` interface is the component, and the `CoffeeDecorator` class is the abstract decorator. The `MilkDecorator` and `SugarDecorator` are concrete decorators that add additional responsibilities to the `Coffee` object.

#### Example - Python

Here's an example of the Decorator pattern in Python:

```python
# Component
class Coffee:
    def get_cost(self):
        pass

    def get_description(self):
        pass

# Concrete Component
class SimpleCoffee(Coffee):
    def get_cost(self):
        return 1.0

    def get_description(self):
        return "Simple coffee"

# Decorator
class CoffeeDecorator(Coffee):
    def __init__(self, coffee):
        self.decorated_coffee = coffee

    def get_cost(self):
        return self.decorated_coffee.get_cost()

    def get_description(self):
        return self.decorated_coffee.get_description()

# Concrete Decorator
class MilkDecorator(CoffeeDecorator):
    def get_cost(self):
        return self.decorated_coffee.get_cost() + 0.5

    def get_description(self):
        return self.decorated_coffee.get_description() + ", milk"

# Concrete Decorator
class SugarDecorator(CoffeeDecorator):
    def get_cost(self):
        return self.decorated_coffee.get_cost() + 0.2

    def get_description(self):
        return self.decorated_coffee.get_description() + ", sugar"

# Usage
simple_coffee = SimpleCoffee()
print(f"{simple_coffee.get_description