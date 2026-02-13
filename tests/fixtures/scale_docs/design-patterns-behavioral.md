---
title: Behavioral Design Patterns
description: Detailed technical documentation on the Observer, Strategy, Command, State, Template Method, Iterator, and Mediator design patterns.
keywords:
  - design patterns
  - behavioral patterns
  - observer
  - strategy
  - command
  - state
  - template method
  - iterator
  - mediator
category: software-engineering
tags:
  - design-patterns
  - software-architecture
  - object-oriented-programming
---

## Observer Pattern

The Observer pattern is a behavioral design pattern that allows objects to be notified of changes to the state of another object. It provides a way to implement event-driven architectures, where an object (the subject) can have any number of dependent objects (observers) that are automatically notified when the subject's state changes.

### Structure

The Observer pattern consists of the following components:

- **Subject**: Maintains a list of its observers and provides methods for attaching and detaching observers.
- **Observer**: Defines an updating interface for objects that should be notified of changes in the subject.
- **ConcreteSubject**: Concrete implementation of the subject. It keeps track of its observers and notifies them of any state changes.
- **ConcreteObserver**: Concrete implementation of the observer. It maintains a reference to the ConcreteSubject instance and updates its state when notified of changes.

### Example Implementation

Here's an example implementation of the Observer pattern in Java:

```java
// Subject interface
public interface Subject {
    void registerObserver(Observer observer);
    void removeObserver(Observer observer);
    void notifyObservers();
}

// Observer interface
public interface Observer {
    void update(double temperature, double humidity, double pressure);
}

// ConcreteSubject
public class WeatherData implements Subject {
    private List<Observer> observers;
    private double temperature;
    private double humidity;
    private double pressure;

    public WeatherData() {
        observers = new ArrayList<>();
    }

    @Override
    public void registerObserver(Observer observer) {
        observers.add(observer);
    }

    @Override
    public void removeObserver(Observer observer) {
        observers.remove(observer);
    }

    @Override
    public void notifyObservers() {
        for (Observer observer : observers) {
            observer.update(temperature, humidity, pressure);
        }
    }

    public void measurementsChanged() {
        notifyObservers();
    }

    public void setMeasurements(double temperature, double humidity, double pressure) {
        this.temperature = temperature;
        this.humidity = humidity;
        this.pressure = pressure;
        measurementsChanged();
    }
}

// ConcreteObserver
public class CurrentConditionsDisplay implements Observer {
    private double temperature;
    private double humidity;
    private Subject weatherData;

    public CurrentConditionsDisplay(Subject weatherData) {
        this.weatherData = weatherData;
        weatherData.registerObserver(this);
    }

    @Override
    public void update(double temperature, double humidity, double pressure) {
        this.temperature = temperature;
        this.humidity = humidity;
        display();
    }

    public void display() {
        System.out.println("Current conditions: " + temperature + "F degrees and " + humidity + "% humidity");
    }
}

// Usage
WeatherData weatherData = new WeatherData();
CurrentConditionsDisplay currentConditionsDisplay = new CurrentConditionsDisplay(weatherData);
weatherData.setMeasurements(80.0, 65.0, 30.4);
```

In this example, the `WeatherData` class is the `ConcreteSubject` that maintains a list of `Observer` instances and notifies them when the weather measurements change. The `CurrentConditionsDisplay` class is a `ConcreteObserver` that updates its state and displays the current conditions when notified by the `WeatherData` subject.

### Applicability

The Observer pattern is useful in the following scenarios:

- **Event-driven architectures**: When you need to implement a publish-subscribe mechanism where objects can subscribe to events or state changes of other objects.
- **Model-View-Controller (MVC) and Model-View-Presenter (MVP) architectures**: The Observer pattern is a key component in these architectural patterns, where the model is the subject, and the views are the observers.
- **Decoupling of components**: The Observer pattern allows you to decouple the subject from its observers, making the system more flexible and easier to maintain.

### Advantages

- **Loose coupling**: Observers are loosely coupled to the subject, allowing you to add or remove observers without affecting the subject or other observers.
- **Flexibility**: You can add new observers at any time, and the subject doesn't need to know about them.
- **Reusability**: The Observer pattern provides a standard way to implement event-driven architectures, making it reusable across different projects.

### Disadvantages

- **Unexpected updates**: Observers may receive unexpected updates if the subject's state changes in ways they don't expect.
- **Memory leaks**: If observers are not properly removed from the subject, it can lead to memory leaks, as the subject will continue to hold references to the observers.
- **Debugging**: Tracing the flow of updates can be more complicated, as the control flow is inverted compared to a traditional function call.

## Strategy Pattern

The Strategy pattern is a behavioral design pattern that allows you to define a family of algorithms, encapsulate each one, and make them interchangeable. It enables the selection of an algorithm at runtime based on the specific requirements of the task at hand.

### Structure

The Strategy pattern consists of the following components:

- **Strategy**: Defines the interface for all supported algorithms.
- **ConcreteStrategy**: Implements the algorithm defined by the Strategy interface.
- **Context**: Uses the Strategy interface to call the algorithm defined by the ConcreteStrategy.

### Example Implementation

Here's an example implementation of the Strategy pattern in Java:

```java
// Strategy interface
public interface SortStrategy {
    void sort(int[] arr);
}

// ConcreteStrategy implementations
public class BubbleSort implements SortStrategy {
    @Override
    public void sort(int[] arr) {
        // Implement bubble sort algorithm
        for (int i = 0; i < arr.length - 1; i++) {
            for (int j = 0; j < arr.length - i - 1; j++) {
                if (arr[j] > arr[j + 1]) {
                    // Swap arr[j] and arr[j+1]
                    int temp = arr[j];
                    arr[j] = arr[j + 1];
                    arr[j + 1] = temp;
                }
            }
        }
    }
}

public class QuickSort implements SortStrategy {
    @Override
    public void sort(int[] arr) {
        // Implement quick sort algorithm
        quickSort(arr, 0, arr.length - 1);
    }

    private void quickSort(int[] arr, int low, int high) {
        if (low < high) {
            int pivotIndex = partition(arr, low, high);
            quickSort(arr, low, pivotIndex - 1);
            quickSort(arr, pivotIndex + 1, high);
        }
    }

    private int partition(int[] arr, int low, int high) {
        // Partition the array and return the pivot index
        // ...
    }
}

// Context
public class SortContext {
    private SortStrategy sortStrategy;

    public void setSortStrategy(SortStrategy sortStrategy) {
        this.sortStrategy = sortStrategy;
    }

    public void sort(int[] arr) {
        sortStrategy.sort(arr);
    }
}

// Usage
SortContext context = new SortContext();

context.setSortStrategy(new BubbleSort());
int[] arr1 = {5, 2, 8, 1, 9};
context.sort(arr1);
// arr1 is now sorted using the BubbleSort strategy

context.setSortStrategy(new QuickSort());
int[] arr2 = {5, 2, 8, 1, 9};
context.sort(arr2);
// arr2 is now sorted using the QuickSort strategy
```

In this example, the `SortStrategy` interface defines the contract for sorting algorithms, and the `BubbleSort` and `QuickSort` classes are the concrete implementations of this interface. The `SortContext` class is the "context" that uses the `SortStrategy` interface to perform the sorting operation, allowing the sorting algorithm to be changed at runtime.

### Applicability

The Strategy pattern is useful in the following scenarios:

- **Algorithms that vary**: When you have a family of algorithms that need to be used interchangeably, the Strategy pattern allows you to encapsulate and select the appropriate algorithm at runtime.
- **Avoid conditional logic**: The Strategy pattern can help eliminate complex conditional logic in your code by encapsulating each algorithm in a separate class.
- **Dynamic behavior**: The Strategy pattern allows you to change the behavior of an object at runtime by changing the strategy it uses.

### Advantages

- **Encapsulation**: Each algorithm is encapsulated in its own class, making the code more modular and easier to maintain.
- **Flexibility**: You can easily add new strategies or modify existing ones without affecting the client code.
- **Avoids conditional logic**: The Strategy pattern helps eliminate complex conditional logic in the client code.

### Disadvantages

- **Complexity**: Introducing the Strategy pattern can increase the complexity of the system by adding more classes and interfaces.
- **Overhead**: Depending on the frequency of strategy changes, the overhead of creating new strategy objects may be significant.
- **Client awareness**: Clients must be aware of the different strategies and their appropriate use cases.

## Command Pattern

The Command pattern is a behavioral design pattern that encapsulates a request as an object, thereby allowing you to parameterize clients with different requests, queue or log requests, and support undoable operations.

### Structure

The Command pattern consists of the following components:

- **Command**: Declares an interface for executing an operation.
- **ConcreteCommand**: Implements the `execute()` method defined by the Command interface, linking the action with the receiver.
- **Receiver**: Knows how to perform the operations associated with carrying out a request. Any class can be a Receiver.
- **Invoker**: Asks the command to carry out the request.
- **Client**: Creates a ConcreteCommand object and sets its receiver.

### Example Implementation

Here's an example implementation of the Command pattern in Java:

```java
// Command interface
public interface Command {
    void execute();
    void undo();
}

// ConcreteCommand
public class LightOnCommand implements Command {
    private Light light;

    public LightOnCommand(Light light) {
        this.light = light;
    }

    @Override
    public void execute() {
        light.on();
    }

    @Override
    public void undo() {
        light.off();
    }
}

// Receiver
public class Light {
    public void on() {
        System.out.println("Light is on");
    }

    public void off() {
        System.out.println("Light is off");
    }
}

// Invoker
public class RemoteControl {
    private Command command;

    public void setCommand(Command command) {
        this.command = command;
    }

    public void pressButton() {
        command.execute();
    }

    public void undoButton() {
        command.undo();
    }
}

// Client
public class Main {
    public static void main(String[] args) {
        Light light = new Light();
        Command lightOnCommand = new LightOnCommand(light);

        RemoteControl remoteControl = new RemoteControl();
        remoteControl.setCommand(lightOnCommand);
        remoteControl.pressButton(); // Prints "Light is on"
        remoteControl.undoButton(); // Prints "Light is off"
    }
}
```

In this example, the `LightOnCommand` is a `ConcreteCommand` that encapsulates the request to turn on a `Light` object (the `Receiver`). The `RemoteControl` class is the `Invoker` that holds the `Command` object and executes it when the `pressButton()` method is called. The `undo()` method is also implemented to revert the executed command.

### Applicability

The Command pattern is useful in the following scenarios:

- **Parameterize objects with actions**: When you want to pass methods as arguments to other methods or store them in data structures.
- **Queue or log requests**: When you need to queue, schedule, or log requests, the Command pattern provides a way to do this.
- **Implement undo and redo**: The Command pattern makes it easy to implement undo and redo functionality, as each command can be undone by executing its undo() method.
- **Decouple the invoker from the receiver**: The Command pattern decouples the object that invokes the operation from the one that knows how to perform it.

### Advantages

- **Encapsulation**: The Command pattern encapsulates a request as an object, making it easier to extend and modify the system.
- **Flexibility**: The Command pattern allows you to add new commands without modifying the invoker or the receiver.
- **Undo and redo**: The Command pattern makes it easy to implement undo and redo functionality.
- **Logging and queueing**: The Command pattern makes it easy to log or queue commands for later execution.

### Disadvantages

- **Increased complexity**: The Command pattern can increase the complexity of the system by introducing additional classes and objects.
- **Overhead**: Depending on the frequency of command execution, the overhead of creating new command objects may be significant.
- **Potential memory leaks**: If the invoker holds a reference to a command object that is no longer needed, it can lead to memory leaks.

## State Pattern

The State pattern is a behavioral design pattern that allows an object to alter its behavior when its internal state changes. The object will appear to change its class.

### Structure

The State pattern consists of the following components:

- **Context**: Maintains an instance of a ConcreteState subclass that defines the current state.
- **State**: Defines an interface for encapsulating the behavior associated with a particular state of the Context.
- **ConcreteState**: Implements a behavior associated with a state of the Context.

### Example Implementation

Here's an example implementation of the State pattern in Java:

```java
// Context
public class TVContext {
    private TVState state;

    public TVContext() {
        this.state = new TVOffState();
    }

    public void setState(TVState state) {
        this.state = state;
    }

    public void pressButton() {
        state.handleButton(this);
    }
}

// State interface
public interface TVState {
    void handleButton(TVContext context);
}

// Concrete State implementations
public class TVOffState implements TVState {
    @Override
    public void handleButton(TVContext context) {
        System.out.println("Turning TV on");
        context.setState(new TVOnState());
    }
}

public class TVOnState implements TVState {
    @Override
    public void handleButton(TVContext context) {
        System.out.println("Turning TV off");
        context.setState(new TVOffState());
    }
}

// Usage
public class Main {
    public static void main(String[] args) {
        TVContext context = new TVContext();
        context.pressButton(); // Prints "Turning TV on"
        context.pressButton(); // Prints "Turning TV off"
    }
}
```

In this example, the `TVContext` class is the `Context` that maintains the current state of the TV. The `TVState` interface defines the contract for the different states, and the `TVOffState` and `TVOnState` are the `ConcreteState` implementations. When the `pressButton()` method is called, the current state handles the button press and updates the state of the `TVContext` accordingly.

### Applicability

The State pattern is useful in the following scenarios:

- **Behavior depends on state**: When an object's behavior is determined by its state, and it must change its behavior at runtime depending on that state.
- **Complex conditional statements**: When you have a lot of conditional statements that depend on the object's state.
- **State-specific actions**: When you want to organize state-specific logic into separate classes.

### Advantages

- **Encapsulation**: The State pattern encapsulates state-specific behavior into separate classes, making the code more modular and easier to maintain.
- **Flexibility**: The State pattern makes it easy to add new states or modify existing ones without affecting the client code.
- **Avoid complex conditional logic**: The State pattern helps you avoid complex conditional statements in your code by encapsulating them in separate state classes.

### Disadvantages

- **Increased complexity**: The State pattern can increase the complexity of the system by introducing more classes and objects.
- **Overhead**: Depending on the frequency of state changes, the overhead of creating new state objects may be significant.
- **Difficulty in tracking state changes**: It can be challenging to keep track of the object's current state, especially when there are many possible states.

## Template Method Pattern

The