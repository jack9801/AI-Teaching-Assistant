FROM maven:3.9.9-eclipse-temurin-21 AS build
WORKDIR /workspace
COPY pom.xml .
COPY src ./src
RUN mvn -q -DskipTests package

FROM eclipse-temurin:21-jre
WORKDIR /app
COPY --from=build /workspace/target/gateway-0.1.0.jar /app/gateway.jar
EXPOSE 8080
ENTRYPOINT ["java","-jar","/app/gateway.jar"]
